# Job Scraping Agent

An automated job scraping tool that collects job postings from LinkedIn and Indeed using Python and Selenium.

## Features

- Scrapes job listings from LinkedIn and Indeed
- Automated browser handling using Selenium
- Data extraction and processing
- Configurable search parameters

## Requirements

- Python 3.11+
- Chrome browser
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Configure the settings in `config/config.json`

## Usage

Run the main job agent script:
```bash
python src/job_agent.py
```

## Project Structure

```
├── config/
│   └── config.json     # Configuration settings
├── src/
│   ├── browser_handler.py    # Browser automation handling
│   ├── indeed_agent.py       # Indeed specific scraping
│   ├── job_scraper.py       # Core scraping functionality
│   ├── linkedin_scraper.py  # LinkedIn specific scraping
│   └── job_agent.py         # Main application entry
├── tests/               # Test files
└── requirements.txt     # Python dependencies
```

## License

[Your chosen license]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.