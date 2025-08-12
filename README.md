# Legal Case Analysis Tool

This tool uses the ChatGPT API to analyze legal case PDF files and identify defendant company information.

## File Structure

```
project/
├── main.py
├── main_json_processor.py
├── config.py
├── chatgpt_client.py
├── pdf_processor.py 
├── json_config.py
├── requirements.txt
├── pdfs/
├── json_files/
└── analysis_results.json
```

## Installation Steps

1. **Create Project Directory**
```bash
mkdir legal_case_analysis
cd legal_case_analysis
```

2. **Install Python Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure API Key**
   - Edit the `config.py` file
   - Replace `API_KEY` with your actual API key

4. **Prepare PDF Files**
   - Place 20 PDF files into the `pdfs/` directory
   - The program will automatically process all PDF files in this directory

## Usage

1. **Run the Program**
```bash
python main.py
```

2. **View Results**
   - Results will be saved in the `analysis_results.json` file
   - Each case will return results in standard JSON format

## Configuration Details

You can modify the following in `config.py`:

- `API_KEY`: Your OpenAI API key
- `MODEL`: The model to use (recommended: gpt-4)
- `PDF_DIRECTORY`: Path to the PDF file directory
- `OUTPUT_FILE`: Path to the output results file
- `MAX_TOKENS`: Maximum token count for API responses
- `TEMPERATURE`: Temperature parameter (0.1 ensures consistency)

## Output Format

The analysis result for each case includes:

```json
{
  "Case ID": "Case ID",
  "Filename": "PDF filename",
  "Defendant Type": "Individual Only or Individual and Company", 
  "ExtractedComapny_Individual": "Related companies of individual defendants (separated by ;)",
  "ExtractedComapny_Both": "Company defendants (separated by ;)",
  "ExtractEvidence": "Evidence sentences (format: company name => sentence)"
}
```

## Notes

1. **API Limitations**: The program automatically handles API rate limits, including retry mechanisms
2. **PDF Quality**: Ensure that PDF files can extract text content properly
3. **Cost Control**: Each PDF file will make one API call, so be mindful of usage costs
4. **Error Handling**: The program will skip files that cannot be processed and continue execution

## Troubleshooting

1. **PDF Read Failure**: The program will attempt two PDF processing methods (PyPDF2 and PyMuPDF)
2. **API Call Failure**: Includes retry mechanisms and detailed error logs
3. **JSON Parsing Errors**: Cleans response content and retries

## Extension Features

You can modify as needed:

- `pdf_processor.py`: Adjust text extraction and defendant identification logic
- `chatgpt_client.py`: Modify prompts or API parameters
- `config.py`: Add more configuration options