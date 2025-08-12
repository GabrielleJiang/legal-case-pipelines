"""
Main function to process JSON files and analyze cases using ChatGPT API.
This script reads JSON files containing case data and sends them to ChatGPT for analysis.
It saves the results in a JSON file and tracks failed cases with detailed logging.
"""

import os
import json
import time
from datetime import datetime
from chatgpt_client import ChatGPTClient
from json_config import JsonConfig

def load_json_file(file_path: str) -> dict:
    """Load and parse JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error in {file_path}: {str(e)}")
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
        return None

def validate_case_data(case_data: dict) -> bool:
    """Validate that case data has required fields"""
    if "CaseID" not in case_data and "index" not in case_data:
        print("Missing required field: CaseID or index")
        return False
    
    if "def_key" not in case_data:
        print("Missing required field: def_key")
        return False
    
    if "Background" not in case_data and "background" not in case_data:
        print("Missing required field: Background or background")
        return False
    
    return True

def save_failure_log(failed_cases_detail: list, failed_cases_filenames: list, config: JsonConfig):
    """Save failure log to JSON file"""
    try:
        unique_failed_filenames = list(set(failed_cases_filenames))
        
        failure_log = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_failed_cases": len(failed_cases_detail),
                "total_failed_filenames": len(failed_cases_filenames),
                "total_unique_failed_filenames": len(unique_failed_filenames)
            },
            "failed_case_details": failed_cases_detail,
            "failed_case_filenames": failed_cases_filenames,
            "unique_failed_case_filenames": unique_failed_filenames
        }
        
        with open(config.FAILURE_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(failure_log, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Failure log saved to: {config.FAILURE_LOG_FILE}")
        
    except Exception as e:
        print(f"Error saving failure log: {str(e)}")

def main():
    """Main function to process JSON files and analyze cases"""
    config = JsonConfig()
    
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        return
    
    chatgpt_client = ChatGPTClient(config.API_KEY, config.MODEL)
    
    json_directory = config.JSON_DIRECTORY
    results = []
    failed_cases_detail = []
    failed_cases_filenames = []
    
    print(f"Starting to process JSON files from directory: {json_directory}")
    print(f"Processing items from index 51 onwards (skipping first 50 items)")
    
    json_files = [f for f in os.listdir(json_directory) if f.lower().endswith('.json')]
    
    if not json_files:
        print("No JSON files found!")
        return
    
    print(f"Found {len(json_files)} JSON files")
    
    total_processed = 0
    total_successful = 0
    total_failed = 0
    
    for i, json_file in enumerate(json_files, 1):
        try:
            print(f"\nProcessing file {i}/{len(json_files)}: {json_file}")
            
            json_path = os.path.join(json_directory, json_file)
            case_data = load_json_file(json_path)
            
            if case_data is None:
                print(f"Failed to load {json_file}")
                continue
            
            cases_to_process = []
            
            if isinstance(case_data, list):
                if len(case_data) > 50:
                    cases_to_process = case_data[50:]
                    print(f"Found {len(case_data)} cases total, processing {len(cases_to_process)} cases (skipping first 50)")
                else:
                    cases_to_process = []
                    print(f"Found only {len(case_data)} cases, all are in the first 50, nothing to process")
            elif isinstance(case_data, dict):
                cases_to_process = []
                print(f"Found 1 case in this file, skipping (would be in first 50)")
            else:
                print(f"Invalid JSON structure in {json_file}")
                continue
            
            file_processed = 0
            file_successful = 0
            file_failed = 0
            
            if not cases_to_process:
                print("No cases to process in this file (all are in first 50 or file is empty)")
                continue
            
            for case_index, single_case in enumerate(cases_to_process):
                try:
                    actual_case_index = case_index + 51
                    
                    if "Filename" not in single_case or not single_case["Filename"]:
                        if "filename" in single_case:
                            single_case["Filename"] = single_case["filename"]
                        else:
                            single_case["Filename"] = json_file
                    
                    if "CaseID" not in single_case and "index" in single_case:
                        single_case["CaseID"] = single_case["index"]
                    
                    if "Background" not in single_case and "background" in single_case:
                        if isinstance(single_case["background"], str):
                            single_case["Background"] = [single_case["background"]]
                        else:
                            single_case["Background"] = single_case["background"]
                    
                    if not validate_case_data(single_case):
                        error_msg = f"Invalid case data in {json_file}, case {actual_case_index}"
                        print(error_msg)
                        
                        failed_cases_detail.append({
                            "filename": single_case.get("Filename", json_file),
                            "file_source": json_file,
                            "case_index": actual_case_index,
                            "error_type": "Invalid case data",
                            "error_message": "Missing required fields"
                        })
                        failed_cases_filenames.append(single_case.get("Filename", json_file))
                        
                        file_failed += 1
                        continue
                    
                    file_processed += 1
                    total_processed += 1
                    
                    print(f"Processing case {actual_case_index} ({case_index + 1}/{len(cases_to_process)} in remaining batch)")
                    print(f"Defendants: {single_case.get('def_key', 'None')}")
                    
                    print("Calling ChatGPT API for analysis...")
                    analysis_result = chatgpt_client.analyze_case(single_case)
                    
                    if analysis_result:
                        results.append(analysis_result)
                        file_successful += 1
                        total_successful += 1
                        print("Analysis completed ✓")
                    else:
                        # Add to failure tracking
                        failed_cases_detail.append({
                            "filename": single_case.get("Filename", json_file),
                            "file_source": json_file,
                            "case_index": actual_case_index,
                            "error_type": "API analysis failed",
                            "error_message": "ChatGPT API returned no result"
                        })
                        failed_cases_filenames.append(single_case.get("Filename", json_file))
                        
                        file_failed += 1
                        total_failed += 1
                        print("Analysis failed ✗")
                    
                    if case_index < len(cases_to_process) - 1:
                        print(f"Waiting {config.REQUEST_DELAY} seconds...")
                        time.sleep(config.REQUEST_DELAY)
                    
                    if file_processed % 10 == 0 and case_index < len(cases_to_process) - 1:
                        print(f"Completed {file_processed} cases, taking a 5-second break...")
                        time.sleep(5)
                        
                except Exception as e:
                    actual_case_index = case_index + 51
                    error_msg = f"Error processing case {actual_case_index} in {json_file}: {str(e)}"
                    print(error_msg)
                    
                    failed_cases_detail.append({
                        "filename": single_case.get("Filename", json_file),
                        "file_source": json_file,
                        "case_index": actual_case_index,
                        "error_type": "Processing exception",
                        "error_message": str(e)
                    })
                    failed_cases_filenames.append(single_case.get("Filename", json_file))
                    
                    file_failed += 1
                    total_failed += 1
                    continue
            
            print(f"File {json_file} summary: {file_successful} successful, {file_failed} failed (processed {len(cases_to_process)} cases from index 51+)")
                    
        except Exception as e:
            print(f"Error processing {json_file}: {str(e)}")
            continue
    
    print(f"\n" + "="*50)
    print("PROCESSING SUMMARY")
    print("="*50)
    print(f"Total cases processed: {total_processed}")
    print(f"Successful analyses: {total_successful}")
    print(f"Failed analyses: {total_failed}")
    
    if failed_cases_detail:
        print(f"\nFAILED CASE DETAILS ({len(failed_cases_detail)} total):")
        print("-" * 50)
        for i, failure in enumerate(failed_cases_detail, 1):
            print(f"  {i}. File: {failure['filename']}")
            print(f"     Source: {failure['file_source']}, Case: {failure['case_index']}")
            print(f"     Error: {failure['error_type']} - {failure['error_message']}")
            print()
    
    # Print failed cases filenames summary
    if failed_cases_filenames:
        print(f"FAILED CASE FILENAMES ({len(failed_cases_filenames)} total):")
        print("-" * 50)
        unique_failed_files = list(set(failed_cases_filenames))
        for filename in unique_failed_files:
            count = failed_cases_filenames.count(filename)
            print(f"  {filename} (failed: {count})")
    else:
        print("\nNo failed cases!")
    
    if failed_cases_detail:
        save_failure_log(failed_cases_detail, failed_cases_filenames, config)
    
    if results:
        output_file = config.OUTPUT_FILE
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to: {output_file}")
    else:
        print("\n✗ No successful analyses to save")

if __name__ == "__main__":
    main()