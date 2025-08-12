"""
Main function to process JSON files and analyze cases using ChatGPT API.
This script reads JSON files containing case data and sends them to ChatGPT for analysis.
It saves the results in a JSON file with improved error handling and progress saving.
"""

import os
import json
import time
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
    if "CaseID" not in case_data:
        print("Missing required field: CaseID or index")
        return False
    
    if "def_key" not in case_data:
        print("Missing required field: def_key")
        return False
     
    if "Background" not in case_data and "background" not in case_data:
        print("Missing required field: Background or background")
        return False
    
    return True

def save_progress(results: list, output_file: str, temp_suffix: str = "_temp"):
    """Save current progress to a temporary file"""
    temp_file = output_file.replace('.json', f'{temp_suffix}.json')
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"save to: {temp_file}")
    except Exception as e:
        print(f"fail: {str(e)}")

def load_existing_results(output_file: str, temp_suffix: str = "_temp") -> list:
    """Load existing results from temporary file if exists"""
    temp_file = output_file.replace('.json', f'{temp_suffix}.json')
    
    if os.path.exists(temp_file):
        try:
            with open(temp_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"get {len(results)} results")
            return results
        except Exception as e:
            print(f"fail: {str(e)}")
    
    return []

def get_processed_case_ids(results: list) -> set:
    """Get set of already processed case IDs"""
    processed_ids = set()
    for result in results:
        case_id = result.get("Case ID") or result.get("CaseID")
        if case_id:
            processed_ids.add(str(case_id))
    return processed_ids

def main():
    """Main function to process JSON files and analyze cases"""
    config = JsonConfig()
    
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        return
    
    chatgpt_client = ChatGPTClient(config.API_KEY, config.MODEL, config)
    
    json_directory = config.JSON_DIRECTORY
    output_file = config.OUTPUT_FILE
    
    results = load_existing_results(output_file)
    processed_ids = get_processed_case_ids(results)
    
    print(f"Starting to process JSON files from directory: {json_directory}")
    print(f"Already processed {len(results)} cases")
    
    json_files = [f for f in os.listdir(json_directory) if f.lower().endswith('.json')]
    
    if not json_files:
        print("No JSON files found!")
        return
    
    print(f"Found {len(json_files)} JSON files")
    
    total_cases = 0
    successful_cases = len(results)
    failed_cases = 0
    skipped_cases = 0
    
    for i, json_file in enumerate(json_files, 1):
        try:
            print(f"\n{'='*60}")
            print(f"Processing file {i}/{len(json_files)}: {json_file}")
            print(f"{'='*60}")
            
            json_path = os.path.join(json_directory, json_file)
            case_data = load_json_file(json_path)
            
            if case_data is None:
                print(f"Failed to load {json_file}")
                continue
            

            cases_to_process = []
            
            if isinstance(case_data, list):
                cases_to_process = case_data
            elif isinstance(case_data, dict):
                cases_to_process = [case_data]
            else:
                print(f"Invalid JSON structure in {json_file}")
                continue
            
            print(f"Found {len(cases_to_process)} cases in this file")
            

            for case_index, single_case in enumerate(cases_to_process):
                total_cases += 1
                
                try:
                    print(f"\n--- Case {case_index + 1}/{len(cases_to_process)} ---")
                    

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
                        print(f"Invalid case data in {json_file}, case {case_index + 1}")
                        failed_cases += 1
                        continue
                    
                    case_id = str(single_case.get("CaseID", single_case.get("index", "")))
                    if case_id in processed_ids:
                        print(f"Case ID {case_id} already processed, skipping...")
                        skipped_cases += 1
                        continue
                    
                    print(f"Case ID: {case_id}")
                    print(f"Defendants: {single_case.get('def_key', 'None')}")
                    
                    print("Calling ChatGPT API for analysis...")
                    analysis_result = chatgpt_client.analyze_case(single_case)
                    
                    if analysis_result:
                        results.append(analysis_result)
                        processed_ids.add(case_id)
                        successful_cases += 1
                        print("✓ Analysis completed successfully")
                        
                        if successful_cases % 5 == 0:
                            save_progress(results, output_file)
                        
                    else:
                        failed_cases += 1
                        print("✗ Analysis failed")
                    
                    if (i < len(json_files) or case_index < len(cases_to_process) - 1):
                        delay = config.REQUEST_DELAY
                        print(f"Waiting {delay} seconds before next request...")
                        time.sleep(delay)
                    
                    print(f"Progress: {successful_cases} successful, {failed_cases} failed, {skipped_cases} skipped out of {total_cases} total")
                        
                except Exception as e:
                    print(f"Error processing case {case_index + 1} in {json_file}: {str(e)}")
                    failed_cases += 1
                    continue
                    
        except Exception as e:
            print(f"Error processing {json_file}: {str(e)}")
            continue
    
    if results:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        temp_file = output_file.replace('.json', '_temp.json')
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                print(f"Temporary file removed: {temp_file}")
            except Exception as e:
                print(f"Failed to remove temporary file: {str(e)}")
        
        print(f"\n{'='*60}")
        print("✓ Processing completed successfully!")
        print(f"Final results saved to: {output_file}")
        print(f"\nFinal Statistics:")
        print(f"  Total cases found: {total_cases}")
        print(f"  Successfully processed: {successful_cases}")
        print(f"  Failed: {failed_cases}")
        print(f"  Skipped (already processed): {skipped_cases}")
        print(f"  Success rate: {(successful_cases/max(total_cases-skipped_cases,1)*100):.1f}%")
        print(f"{'='*60}")
    else:
        print("\n✗ No files processed successfully")

if __name__ == "__main__":
    main()