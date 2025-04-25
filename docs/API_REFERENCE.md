# API Reference: MCP & AI Agent Endpoints

## MCP Function Endpoints

### List Functions
- **GET** `/api/mcp/functions`
- **Description:** Returns all available MCP functions and metadata.

### Execute Function
- **POST** `/api/mcp/function/execute`
- **Body:** `{ "function": "function_name", "parameters": { ... } }`
- **Returns:** JSON result of the function.

### List Workflows
- **GET** `/api/mcp/workflows`
- **Description:** Returns all available MCP workflows and metadata.

### Execute Workflow
- **POST** `/api/mcp/workflow/execute`
- **Body:** `{ "workflow": "workflow_name", "parameters": { ... } }`
- **Returns:** JSON result of the workflow.

---

## Example MCP Functions
- `analyze_tax_distribution` — Analyze levy distribution for a district.
- `analyze_historical_trends` — Get trend insights for a district.
- `predict_levy_rates` — Forecast future levy rates using AI/ML.

---

## Authentication
- Most endpoints require user authentication (JWT or session cookie).
- Admin endpoints require elevated permissions.

---

## Error Handling
- All endpoints return JSON with `error` and `message` fields if a problem occurs.

---

## Further Reading
- See `docs/USER_GUIDE.md` and `docs/ADMIN_GUIDE.md` for usage examples and workflows.
