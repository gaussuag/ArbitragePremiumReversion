# AGENTS.md - Coding Guidelines for ETF Arbitrage Analysis Tool

## Project Overview
Python-based ETF arbitrage analysis tool using AKShare for financial data, pandas for analysis, and Plotly for visualization.

## Build & Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run main analysis
python etf_arbitrage.py

# Run with custom parameters
python etf_arbitrage.py -d 30                    # Last 30 days
python etf_arbitrage.py -s 2024-01-01 -e 2024-12-31  # Date range
python etf_arbitrage.py -t 3.0                   # Custom threshold

# Generate visualization report
python visualize_interactive.py

# View report
start data/report.html        # Windows
open data/report.html         # Mac
xdg-open data/report.html     # Linux
```

## Testing

**No test framework configured.**
To add tests:
```bash
# Install pytest
pip install pytest

# Run tests (when added)
pytest
pytest -v                    # Verbose
pytest -k test_name          # Single test
pytest tests/test_etf.py -v  # Specific file
```

## Code Style Guidelines

### Imports
- Order: stdlib → third-party → local
- Group with blank lines between groups
- Use explicit imports over wildcard

```python
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np
import akshare as ak
import plotly.graph_objects as go
```

### Naming Conventions
- **Functions/Variables**: `snake_case` (e.g., `get_etf_data`, `calculate_r_squared`)
- **Classes**: `PascalCase` (e.g., `ETFDataFetcher`, `GlobalIndexFetcher`)
- **Constants**: `UPPER_CASE` (e.g., `BENCHMARK_CONFIGS`, `DEFAULT_DAYS`)
- **Private methods**: `_leading_underscore` (e.g., `_get_price_data`)

### Docstrings
Use Chinese docstrings following existing style:

```python
def calculate_tracking_error(self, etf_df, index_df):
    """
    计算ETF相对于纳斯达克指数的跟踪误差
    
    Args:
        etf_df: ETF数据 DataFrame (包含 日期, 净值, 收盘)
        index_df: 纳斯达克指数数据 DataFrame (包含 日期, 收盘, 涨跌幅)
    
    Returns:
        DataFrame with columns: 日期, ETF净值涨幅, 指数涨跌幅, 跟踪误差
    """
```

### Error Handling
- Use try-except with informative error messages (in Chinese)
- Print errors instead of raising when graceful degradation is possible
- Always return `None` on failure to allow caller to handle

```python
try:
    df = ak.fund_etf_hist_em(...)
except Exception as e:
    print(f"失败: {e}")
    return None
```

### Data Handling
- Use `pd.to_datetime()` for date conversions
- Handle missing data with `dropna()` or `fillna()`
- Validate DataFrame length before operations
- Use `.copy()` when modifying DataFrames to avoid SettingWithCopyWarning

### Configuration
- Read from `config.json` using `load_config()` pattern
- Provide sensible defaults when config missing
- Support command-line arguments via `argparse`

### Output
- Print progress messages in Chinese with clear indicators (✓, ✗, △)
- Save results to `data/` directory as CSV and HTML
- Use `Path` for cross-platform path handling

### Type Hints (Optional but Recommended)
When adding new code, consider type hints:

```python
from typing import Optional, Dict, List

def get_etf_data(self, etf_code: str, start_date: Optional[str] = None) -> Optional[pd.DataFrame]:
```

## Project Structure

```
.
├── etf_arbitrage.py          # Core analysis logic
├── visualize_interactive.py  # Plotly visualization
├── config.json               # ETF codes & settings
├── requirements.txt          # Dependencies
├── data/                     # Output directory (gitignored)
│   ├── *.csv                # Data exports
│   ├── cache/               # Cached API responses
│   └── report.html          # Generated report
└── docs/                     # Documentation
```

## Key Dependencies
- `akshare>=1.10.0` - Chinese financial data API
- `pandas>=1.3.0` - Data manipulation
- `numpy>=1.20.0` - Numerical computing
- `plotly>=5.0.0` - Interactive visualization

## Important Notes
- Data is cached in `data/cache/` to avoid repeated API calls
- API rate limits may apply - respect AKShare guidelines
- Always check DataFrame is not None before accessing
- Chinese comments and output are intentional for target users
