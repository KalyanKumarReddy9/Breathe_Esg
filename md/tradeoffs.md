# Tradeoffs

- **Authentication deferred**: API endpoints are open in the prototype to focus on data flow; production would require auth and tenant scoping.
- **Outlier detection deferred**: No statistical anomaly detection yet; flagged status comes from parse/validation only.
- **Limited airport lookup**: Travel distance uses a local IATA subset to avoid external dependencies.
- **Frontend simplicity**: Review UI favors speed over advanced analytics or charts beyond basic summaries.
