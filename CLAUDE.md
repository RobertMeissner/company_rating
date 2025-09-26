# Company Rating Scraper

## Project Overview
A personal tool to automatically gather company ratings and career information for job hunting research. Targets ~200 companies with monthly updates.

## Business Context
- **Problem**: Need to research company ratings (Kununu, Glassdoor) and find career pages for job applications
- **Scale**: 200 companies, adding ~5-10 weekly, full refresh monthly/yearly
- **Success Criteria**: 80%+ automation success rate
- **User**: Single fullstack developer, personal use

## Technical Approach
- **Primary**: Playwright-based scraping with stealth techniques
- **Data Storage**: SQLite for simplicity and zero cost
- **Architecture**: Single Python script initially, evolve to modular structure
- **Error Handling**: Graceful failures with manual fallback tracking

## Key Components

### Core Scraping Functions
1. `scrape_kununu_rating(company_name)` - Extract Kununu ratings
2. `scrape_glassdoor_rating(company_name)` - Extract Glassdoor ratings  
3. `find_career_page(company_name)` - Locate careers/jobs page
4. `search_company_info(company_name)` - Orchestrate all lookups

### Infrastructure
1. **Rate limiting**: Random delays, respectful scraping
2. **User agent rotation**: Avoid detection patterns
3. **Error tracking**: Log failures for manual review
4. **Data validation**: Ensure scraped data quality
5. **Resume capability**: Handle interrupted runs

### Data Model
```python
CompanyInfo:
  - name: str
  - kununu_rating: Optional[float]
  - kununu_url: Optional[str]
  - glassdoor_rating: Optional[float] 
  - glassdoor_url: Optional[str]
  - career_page: Optional[str]
  - last_updated: datetime
  - scrape_status: str  # success, partial, failed
```

## Development Phases

### Phase 1: MVP (Week 1-2)
- [x] Basic Kununu scraping with tests
- [ ] Glassdoor scraping
- [ ] Career page detection
- [ ] SQLite storage
- [ ] CSV import/export

### Phase 2: Production Ready (Week 3-4)
- [ ] Error handling and retry logic
- [ ] User agent rotation
- [ ] Progress tracking and resume capability
- [ ] Data validation and cleaning
- [ ] Full test suite

### Phase 3: Maintenance (Ongoing)
- [ ] Handle website changes
- [ ] Update selectors when they break
- [ ] Add new data sources
- [ ] Performance optimization

## Technical Constraints
- **Budget**: Zero - no paid APIs or services
- **Legal**: Respectful scraping, aware of ToS violations
- **Maintenance**: Minimal ongoing effort required
- **Reliability**: Handle failures gracefully, don't break on edge cases

## File Structure
```
company-scraper/
├── claude.md                 # This file
├── agents/
│   ├── scraping-agent.md     # Scraping specialist
│   ├── testing-agent.md      # Testing specialist
│   └── data-agent.md         # Data modeling specialist
├── src/
│   ├── main.py              # Entry point
│   ├── scrapers/
│   │   ├── kununu.py        # Kununu-specific scraping
│   │   ├── glassdoor.py     # Glassdoor-specific scraping
│   │   └── career_finder.py # Career page detection
│   ├── models/
│   │   └── company.py       # Data models
│   └── utils/
│       ├── browser.py       # Playwright setup
│       ├── storage.py       # SQLite operations
│       └── rate_limit.py    # Rate limiting utilities
├── tests/
│   ├── test_kununu.py       # Kununu scraper tests
│   ├── test_glassdoor.py    # Glassdoor scraper tests
│   └── test_integration.py  # End-to-end tests
├── data/
│   ├── companies.csv        # Input company list
│   ├── results.db          # SQLite database
│   └── failed_lookups.csv   # Manual review queue
├── requirements.txt
└── README.md
```

## Usage Examples

### Basic Usage
```bash
# Run full scraping pipeline
python src/main.py --input data/companies.csv --output data/results.db

# Resume interrupted run
python src/main.py --resume

# Export results to CSV
python src/main.py --export data/results.csv

# Test specific company
python src/main.py --test "SAP"
```

### Development Workflow
```bash
# Run tests
pytest tests/ -v

# Test specific scraper
python -m pytest tests/test_kununu.py::test_scrape_sap -v

# Run with debug logging
python src/main.py --debug --limit 5
```

## Monitoring & Maintenance

### Success Metrics
- **Automation Rate**: % of companies with complete data
- **Data Freshness**: Age of scraped information
- **Error Rate**: % of failed scraping attempts
- **Coverage**: Companies with at least one rating source

### Failure Modes & Responses
- **IP Blocking**: Implement longer delays, proxy rotation
- **DOM Changes**: Update CSS selectors, XPath expressions
- **Rate Limiting**: Respect robots.txt, implement backoff
- **Data Quality**: Validate ratings are numeric, URLs are valid

### Manual Review Process
1. Export failed companies to CSV
2. Manual research for high-priority targets
3. Update company database with manual findings
4. Track common failure patterns for automation

## Next Steps
1. Complete Kununu PoC and validate approach
2. Extend to Glassdoor with similar pattern
3. Add career page detection
4. Build data storage and export functionality
5. Create monitoring dashboard for scraping health

## Notes
- Focus on German market initially (Kununu strength)
- Consider XING as additional data source for German companies
- Keep scraping respectful - we're not competing with these sites
- Document selector changes for future maintenance