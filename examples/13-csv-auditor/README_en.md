# CSV auditing and report correction

Python calculates exact CSV metrics, the model proposes cleaning steps, and Python checks reported values and types. Incorrect reports are corrected up to three times. The CSV is never modified.

```bash
.venv/bin/sgraph examples/13-csv-auditor/workflow_en.md -- --demo
.venv/bin/sgraph examples/13-csv-auditor/workflow_en.md -- --data /path/to/records.csv --input 'Check data quality and suggest cleaning steps'
```

CSV requires `id`, `amount` and `customer` columns. Row numbers refer to the original file, with the header as row 1. The default sample has 5 records, a parseable amount total of 30.50, duplicate ID A2, an invalid amount on line 5 and a missing customer on line 6. Amounts use Decimal. The total includes duplicates and is not a deduplicated business net amount.

Flow: Load → Draft(pyfunction) → Validate(router) → Render / Draft / Failure. `metrics` is a native Python State field. pyfunction supplies metrics as model material. The prompt requests JSON, which Python validates; this does not use an unimplemented output-schema DSL.

Useful for checks before batch imports. Format and numeric values can be verified; business advice still needs review. This provides neither financial decisions nor automatic accounting corrections. The model receives metrics and the request, not raw customer records.
