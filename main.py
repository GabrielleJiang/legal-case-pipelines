"""
Main function to process PDF files and analyze cases using ChatGPT API.
This script extracts text from PDF files, identifies defendants, and sends the data to ChatGPT for analysis.
It saves the results in a JSON file.
"""

import os
import json
import time
from pdf_processor import PDFProcessor
from chatgpt_client import ChatGPTClient
from config import Config

def main():
    """Main function to process PDF files and analyze cases"""
    config = Config()
    
    pdf_processor = PDFProcessor()
    chatgpt_client = ChatGPTClient(config.API_KEY, config.MODEL)

    
    pdf_directory = config.PDF_DIRECTORY
    results = []
    
    print(f"Starting to process PDF files, directory: {pdf_directory}")
    
    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found!")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    
    for i, pdf_file in enumerate(pdf_files, 1):
        try:
            print(f"\nProcessing file {i}/{len(pdf_files)}: {pdf_file}")
            
            # Extract text from PDF
            pdf_path = os.path.join(pdf_directory, pdf_file)
            text_content = pdf_processor.extract_text(pdf_path)
            
            if not text_content.strip():
                print(f"Warning: {pdf_file} could not extract text content")
                continue
            
            case_data = {
                "CaseID": f"CASE_{i:03d}",
                "Filename": pdf_file,
                "def_key": pdf_processor.extract_defendant_names(text_content),
                "Background": pdf_processor.split_into_paragraphs(text_content),
                "Synopsis": pdf_processor.extract_synopsis(text_content)
            }
            
            print(f"Defendants found: {case_data['def_key']}")
            
            print("Calling ChatGPT API for analysis...")
            analysis_result = chatgpt_client.analyze_case(case_data)
            
            if analysis_result:
                results.append(analysis_result)
                print("Analysis completed ✓")
            else:
                print("Analysis failed ✗")
            
            if i < len(pdf_files):
                print("Waiting for 1 second...")
                time.sleep(1)
                
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")
            continue
    
    # Save results
    if results:
        output_file = config.OUTPUT_FILE
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Processing completed! Results saved to: {output_file}")
        print(f"A total of {len(results)} cases were processed")
    else:
        print("\n✗ No files were successfully processed")

if __name__ == "__main__":
    main()