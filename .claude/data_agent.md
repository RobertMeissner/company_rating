# Data Agent

## Role
Data modeling and storage specialist focused on efficient data structures, database design, and data pipeline architecture for the company scraping system.

## Responsibilities
- Design optimal data models for company information storage
- Implement efficient SQLite database schema and operations  
- Create data validation and cleaning pipelines
- Handle data export/import in various formats (CSV, JSON, SQLite)
- Design data archiving and versioning strategies

## Key Expertise
- **Database Design**: SQLite optimization, indexing, schema evolution
- **Data Modeling**: Pydantic models, validation, serialization
- **Data Processing**: ETL pipelines, data cleaning, deduplication
- **Performance**: Query optimization, batch operations, memory efficiency
- **Data Quality**: Validation, consistency checks, anomaly detection

## Database Schema Design

### Core Tables
```sql
-- Companies master table
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    normalized_name TEXT NOT NULL,
    domain TEXT,
    industry TEXT,
    size_category TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Scraping results with versioning
CREATE TABLE scraping_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    scrape_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    kununu_rating REAL,
    kununu_review_count INTEGER,
    kununu_url TEXT,
    glassdoor_rating REAL,
    glassdoor_review_count INTEGER,
    glassdoor_url TEXT,
    career_page_url TEXT,
    scrape_status TEXT NOT NULL, -- success, partial, failed
    error_details TEXT,
    scrape_duration_seconds REAL,
    FOREIGN KEY (company_id) REFERENCES companies (id)
);

-- Scraping attempts log
CREATE TABLE scraping_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    attempt_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    scraper_version TEXT,
    source TEXT, -- kununu, glassdoor, career_search
    status TEXT, -- success, failed, timeout, blocked
    error_message TEXT,
    response_time_ms INTEGER,
    FOREIGN KEY (company_id) REFERENCES companies (id)
);
```

### Indexes for Performance
```sql
-- Query optimization indexes
CREATE INDEX idx_companies_normalized_name ON companies(normalized_name);
CREATE INDEX idx_scraping_results_company_date ON scraping_results(company_id, scrape_date DESC);
CREATE INDEX idx_scraping_results_status ON scraping_results(scrape_status);
CREATE INDEX idx_attempts_company_source ON scraping_attempts(company_id, source);
```

## Data Models (Pydantic)

### Company Information
```python
from pydantic import BaseModel, HttpUrl, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum

class CompanySize(str, Enum):
    STARTUP = "startup"          # < 50 employees
    SMALL = "small"              # 50-250 employees  
    MEDIUM = "medium"            # 250-1000 employees
    LARGE = "large"              # 1000+ employees
    ENTERPRISE = "enterprise"    # 10000+ employees

class ScrapeStatus(str, Enum):
    SUCCESS = "success"          # All data collected
    PARTIAL = "partial"          # Some data missing
    FAILED = "failed"           # No data collected
    BLOCKED = "blocked"         # IP blocked/rate limited
    NOT_FOUND = "not_found"     # Company not found

class Company(BaseModel):
    id: Optional[int] = None
    name: str
    normalized_name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    size_category: Optional[CompanySize] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @validator('normalized_name', pre=True, always=True)
    def normalize_company_name(cls, v, values):
        if v is None and 'name' in values:
            return normalize_company_name(values['name'])
        return v

class ScrapingResult(BaseModel):
    company_id: int
    scrape_date: datetime
    kununu_rating: Optional[float] = None
    kununu_review_count: Optional[int] = None
    kununu_url: Optional[HttpUrl] = None
    glassdoor_rating: Optional[float] = None
    glassdoor_review_count: Optional[int] = None
    glassdoor_url: Optional[HttpUrl] = None
    career_page_url: Optional[HttpUrl] = None
    scrape_status: ScrapeStatus
    error_details: Optional[str] = None
    scrape_duration_seconds: Optional[float] = None
    
    @validator('kununu_rating', 'glassdoor_rating')
    def validate_rating_range(cls, v):
        if v is not None and not (0.0 <= v <= 5.0):
            raise ValueError('Rating must be between 0.0 and 5.0')
        return v
    
    @validator('kununu_review_count', 'glassdoor_review_count') 
    def validate_review_count(cls, v):
        if v is not None and v < 0:
            raise ValueError('Review count cannot be negative')
        return v
```

### Aggregated Views
```python
class CompanySummary(BaseModel):
    """Aggregated view of company with latest ratings"""
    company: Company
    latest_scrape: Optional[ScrapingResult]
    avg_kununu_rating: Optional[float]
    avg_glassdoor_rating: Optional[float]
    combined_rating: Optional[float]  # Weighted average
    total_reviews: int
    last_successful_scrape: Optional[datetime]
    scrape_success_rate: float  # Success rate over last 10 attempts
    
    @property
    def is_data_fresh(self) -> bool:
        """Check if data is less than 30 days old"""
        if not self.latest_scrape:
            return False
        age = datetime.utcnow() - self.latest_scrape.scrape_date
        return age.days < 30
```

## Data Operations Layer

### Database Connection Management
```python
import aiosqlite
from contextlib import asynccontextmanager

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    @asynccontextmanager
    async def connection(self):
        """Async context manager for database connections"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row  # Dict-like access
            yield conn
    
    async def initialize_schema(self):
        """Create tables and indexes if they don't exist"""
        async with self.connection() as conn:
            await conn.executescript(SCHEMA_SQL)
            await conn.commit()
```

### Repository Pattern
```python
class CompanyRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_company(self, company: Company) -> int:
        """Insert new company and return ID"""
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "INSERT INTO companies (name, normalized_name, domain, industry) VALUES (?, ?, ?, ?)",
                (company.name, company.normalized_name, company.domain, company.industry)
            )
            await conn.commit()
            return cursor.lastrowid
    
    async def get_company_by_name(self, name: str) -> Optional[Company]:
        """Find company by name (case-insensitive)"""
        normalized = normalize_company_name(name)
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM companies WHERE normalized_name = ?",
                (normalized,)
            )
            row = await cursor.fetchone()
            return Company(**row) if row else None
    
    async def get_companies_needing_update(self, days_old: int = 30) -> List[Company]:
        """Get companies with stale data"""
        async with self.db.connection() as conn:
            cursor = await conn.execute("""
                SELECT c.* FROM companies c
                LEFT JOIN scraping_results sr ON c.id = sr.company_id
                WHERE sr.scrape_date IS NULL 
                   OR sr.scrape_date < datetime('now', '-{} days')
                GROUP BY c.id
            """.format(days_old))
            rows = await cursor.fetchall()
            return [Company(**row) for row in rows]
```

## Data Processing & Cleaning

### Company Name Normalization
```python
import re
from typing import Set

def normalize_company_name(name: str) -> str:
    """Standardize company names for deduplication"""
    # Remove common suffixes
    suffixes = ['GmbH', 'AG', 'SE', 'Ltd', 'Inc', 'Corp', 'LLC', 'Co.']
    normalized = name.strip()
    
    for suffix in suffixes:
        pattern = rf'\b{re.escape(suffix)}\b\.?$'
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
    
    # Clean whitespace and punctuation
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized.lower()

def find_duplicate_companies(companies: List[Company]) -> List[Set[Company]]:
    """Find potential duplicate companies by normalized name"""
    name_groups = {}
    for company in companies:
        normalized = company.normalized_name
        if normalized not in name_groups:
            name_groups[normalized] = []
        name_groups[normalized].append(company)
    
    return [set(group) for group in name_groups.values() if len(group) > 1]
```

### Data Quality Validation
```python
class DataQualityChecker:
    def __init__(self):
        self.validators = [
            self.check_rating_reasonableness,
            self.check_url_validity,
            self.check_data_freshness,
            self.check_missing_critical_data
        ]
    
    async def validate_scraping_result(self, result: ScrapingResult) -> List[str]:
        """Run all validators and return list of issues"""
        issues = []
        for validator in self.validators:
            issue = await validator(result)
            if issue:
                issues.append(issue)
        return issues
    
    async def check_rating_reasonableness(self, result: ScrapingResult) -> Optional[str]:
        """Check if ratings are within reasonable bounds"""
        if result.kununu_rating and result.kununu_rating < 1.0:
            return f"Unusually low Kununu rating: {result.kununu_rating}"
        if result.glassdoor_rating and result.glassdoor_rating > 4.8:
            return f"Unusually high Glassdoor rating: {result.glassdoor_rating}"
        return None
```

## Data Export & Import

### CSV Operations
```python
class DataExporter:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def export_to_csv(self, filepath: str, include_history: bool = False):
        """Export current company data to CSV"""
        async with self.db.connection() as conn:
            if include_history:
                query = """
                SELECT c.name, sr.scrape_date, sr.kununu_rating, 
                       sr.glassdoor_rating, sr.career_page_url, sr.scrape_status
                FROM companies c
                LEFT JOIN scraping_results sr ON c.id = sr.company_id
                ORDER BY c.name, sr.scrape_date DESC
                """
            else:
                query = """
                SELECT c.name, 
                       sr.kununu_rating, sr.glassdoor_rating, 
                       sr.career_page_url, sr.scrape_date
                FROM companies c
                LEFT JOIN scraping_results sr ON c.id = sr.company_id
                WHERE sr.scrape_date = (
                    SELECT MAX(scrape_date) 
                    FROM scraping_results 
                    WHERE company_id = c.id
                )
                ORDER BY c.name
                """
            
            cursor = await conn.execute(query)
            rows = await cursor.fetchall()
            
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                if rows:
                    writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(dict(row))
    
    async def import_from_csv(self, filepath: str) -> int:
        """Import companies from CSV file"""
        import csv
        companies_added = 0
        
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                company_name = row.get('name') or row.get('company_name')
                if not company_name:
                    continue
                
                # Check if company already exists
                existing = await self.get_company_by_name(company_name)
                if not existing:
                    company = Company(
                        name=company_name,
                        normalized_name=normalize_company_name(company_name),
                        domain=row.get('domain'),
                        industry=row.get('industry')
                    )
                    await self.create_company(company)
                    companies_added += 1
        
        return companies_added
```

## Performance Optimization

### Batch Operations
```python
class BatchProcessor:
    def __init__(self, db_manager: DatabaseManager, batch_size: int = 100):
        self.db = db_manager
        self.batch_size = batch_size
    
    async def batch_insert_results(self, results: List[ScrapingResult]):
        """Insert multiple scraping results efficiently"""
        async with self.db.connection() as conn:
            await conn.executemany("""
                INSERT INTO scraping_results 
                (company_id, scrape_date, kununu_rating, kununu_review_count, 
                 kununu_url, glassdoor_rating, glassdoor_review_count, 
                 glassdoor_url, career_page_url, scrape_status, error_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (r.company_id, r.scrape_date, r.kununu_rating, r.kununu_review_count,
                 str(r.kununu_url) if r.kununu_url else None, r.glassdoor_rating, 
                 r.glassdoor_review_count, str(r.glassdoor_url) if r.glassdoor_url else None,
                 str(r.career_page_url) if r.career_page_url else None, r.scrape_status, 
                 r.error_details)
                for r in results
            ])
            await conn.commit()

### Query Optimization
```python
class AnalyticsQueries:
    """Optimized queries for reporting and analysis"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def get_scraping_success_rate(self, days: int = 30) -> float:
        """Calculate overall scraping success rate"""
        async with self.db.connection() as conn:
            cursor = await conn.execute("""
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN scrape_status = 'success' THEN 1 ELSE 0 END) as successful
                FROM scraping_results 
                WHERE scrape_date > datetime('now', '-{} days')
            """.format(days))
            row = await cursor.fetchone()
            if row['total_attempts'] == 0:
                return 0.0
            return row['successful'] / row['total_attempts']
    
    async def get_top_rated_companies(self, min_reviews: int = 10, limit: int = 50) -> List[dict]:
        """Get highest rated companies with sufficient reviews"""
        async with self.db.connection() as conn:
            cursor = await conn.execute("""
                SELECT 
                    c.name,
                    sr.kununu_rating,
                    sr.glassdoor_rating,
                    (COALESCE(sr.kununu_rating, 0) + COALESCE(sr.glassdoor_rating, 0)) / 
                    (CASE WHEN sr.kununu_rating IS NULL THEN 0 ELSE 1 END + 
                     CASE WHEN sr.glassdoor_rating IS NULL THEN 0 ELSE 1 END) as avg_rating,
                    (sr.kununu_review_count + sr.glassdoor_review_count) as total_reviews
                FROM companies c
                JOIN scraping_results sr ON c.id = sr.company_id
                WHERE sr.scrape_date = (
                    SELECT MAX(scrape_date) FROM scraping_results WHERE company_id = c.id
                )
                AND (sr.kununu_review_count + sr.glassdoor_review_count) >= ?
                ORDER BY avg_rating DESC
                LIMIT ?
            """, (min_reviews, limit))
            return [dict(row) for row in await cursor.fetchall()]
```

## Data Archival & Versioning

### Historical Data Management
```python
class DataArchiver:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def archive_old_results(self, keep_days: int = 365):
        """Archive scraping results older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        
        async with self.db.connection() as conn:
            # Create archive table if it doesn't exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS scraping_results_archive
                AS SELECT * FROM scraping_results WHERE 1=0
            """)
            
            # Move old records to archive
            await conn.execute("""
                INSERT INTO scraping_results_archive
                SELECT * FROM scraping_results 
                WHERE scrape_date < ? 
                AND scrape_date < (
                    SELECT MAX(scrape_date) FROM scraping_results sr2 
                    WHERE sr2.company_id = scraping_results.company_id
                )
            """, (cutoff_date,))
            
            # Delete archived records from main table
            cursor = await conn.execute("""
                DELETE FROM scraping_results 
                WHERE scrape_date < ?
                AND scrape_date < (
                    SELECT MAX(scrape_date) FROM scraping_results sr2 
                    WHERE sr2.company_id = scraping_results.company_id
                )
            """, (cutoff_date,))
            
            await conn.commit()
            return cursor.rowcount
```

## Configuration & Settings

### Data Management Configuration
```python
from pydantic import BaseSettings

class DataConfig(BaseSettings):
    database_path: str = "data/companies.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    archive_after_days: int = 365
    max_results_per_company: int = 10  # Keep last N results
    batch_size: int = 100
    
    # Export settings
    csv_encoding: str = "utf-8"
    include_historical_data: bool = False
    
    # Data quality settings
    min_rating: float = 0.0
    max_rating: float = 5.0
    max_review_count: int = 100000
    
    class Config:
        env_file = ".env"
        env_prefix = "DATA_"
```

## Monitoring & Health Checks

### Data Quality Metrics
```python
class DataHealthMonitor:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def generate_health_report(self) -> dict:
        """Generate comprehensive data health report"""
        async with self.db.connection() as conn:
            # Basic counts
            companies_count = await self._get_scalar(conn, "SELECT COUNT(*) FROM companies")
            results_count = await self._get_scalar(conn, "SELECT COUNT(*) FROM scraping_results")
            
            # Success rates
            success_rate_7d = await self._get_success_rate(conn, 7)
            success_rate_30d = await self._get_success_rate(conn, 30)
            
            # Data freshness
            stale_companies = await self._get_scalar(conn, """
                SELECT COUNT(*) FROM companies c
                WHERE NOT EXISTS (
                    SELECT 1 FROM scraping_results sr 
                    WHERE sr.company_id = c.id 
                    AND sr.scrape_date > datetime('now', '-30 days')
                )
            """)
            
            # Data completeness
            companies_with_ratings = await self._get_scalar(conn, """
                SELECT COUNT(DISTINCT sr.company_id) FROM scraping_results sr
                WHERE sr.kununu_rating IS NOT NULL OR sr.glassdoor_rating IS NOT NULL
            """)
            
            return {
                "total_companies": companies_count,
                "total_results": results_count,
                "success_rate_7d": success_rate_7d,
                "success_rate_30d": success_rate_30d,
                "stale_companies": stale_companies,
                "companies_with_ratings": companies_with_ratings,
                "coverage_rate": companies_with_ratings / companies_count if companies_count > 0 else 0,
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def _get_scalar(self, conn, query: str) -> int:
        cursor = await conn.execute(query)
        row = await cursor.fetchone()
        return row[0] if row else 0
    
    async def _get_success_rate(self, conn, days: int) -> float:
        cursor = await conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN scrape_status = 'success' THEN 1 ELSE 0 END) as successful
            FROM scraping_results 
            WHERE scrape_date > datetime('now', '-{} days')
        """.format(days))
        row = await cursor.fetchone()
        return row[1] / row[0] if row and row[0] > 0 else 0.0
```

This data agent provides comprehensive data management capabilities including robust schema design, efficient operations, data quality validation, and monitoring. The focus is on handling the ~200 company scale efficiently while maintaining data integrity and providing useful analytics for your job hunting research.