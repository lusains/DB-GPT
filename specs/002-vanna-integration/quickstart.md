# Quickstart: Vanna AI Integration

Get started with Vanna-enhanced Text-to-SQL in DB-GPT.

## Prerequisites

- DB-GPT installed and running
- At least one database connection configured
- ChromaDB dependency installed (`pip install chromadb`)

## Installation

The Vanna integration is part of `dbgpt-ext`. Ensure you have the storage dependency:

```bash
# If using uv (recommended)
uv pip install dbgpt-ext[storage_chromadb]

# If using pip
pip install dbgpt-ext[storage_chromadb]
```

## Quick Setup (3 Steps)

### Step 1: Train Schema from Database

Auto-extract and train all table DDL from your database:

```bash
# Using API
curl -X POST http://localhost:5670/api/v1/vanna/train-schema/mydb
```

**Response**:
```json
{
  "success": true,
  "tables_trained": 25,
  "message": "Schema training completed: 25 tables"
}
```

### Step 2: Add SQL Examples (Optional but Recommended)

Teach the system your common query patterns:

```bash
curl -X POST http://localhost:5670/api/v1/vanna/train \
  -H "Content-Type: application/json" \
  -d '{
    "db_name": "mydb",
    "type": "sql",
    "content": "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id ORDER BY order_count DESC LIMIT 10",
    "question": "Who are our top 10 customers by order count?"
  }'
```

### Step 3: Start Using ChatWithDbVanna

Select the `ChatWithDbVanna` scene in DB-GPT and start asking questions!

```
User: "Show me the top customers by order count"
System: [Uses trained SQL example as context, generates accurate SQL]
```

## Configuration

Add to your `.env` or configuration:

```env
# Enable Vanna features
VANNA_ENABLED=true

# ChromaDB storage path (default: ./vanna_data)
VANNA_CHROMA_PATH=./vanna_data

# Top-k retrieval settings
VANNA_N_RESULTS_DDL=5
VANNA_N_RESULTS_SQL=5
VANNA_N_RESULTS_DOC=3

# Maximum context tokens
VANNA_MAX_CONTEXT_TOKENS=4000
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/vanna/train` | POST | Add training data |
| `/api/v1/vanna/train-schema/{db_name}` | POST | Auto-train from database |
| `/api/v1/vanna/training-data/{db_name}` | GET | List training data |
| `/api/v1/vanna/training-data/{id}` | DELETE | Delete training data |

## Training Data Types

### DDL (Schema)
```json
{
  "db_name": "mydb",
  "type": "ddl",
  "content": "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))"
}
```

### SQL Examples
```json
{
  "db_name": "mydb",
  "type": "sql",
  "content": "SELECT * FROM users WHERE created_at > NOW() - INTERVAL 7 DAY",
  "question": "Show users registered in the last week"
}
```

### Documentation
```json
{
  "db_name": "mydb",
  "type": "documentation",
  "content": "The 'status' column uses: 1=active, 2=inactive, 3=suspended"
}
```

## Troubleshooting

### No context being retrieved
1. Check if training data exists: `GET /api/v1/vanna/training-data/mydb`
2. Verify ChromaDB path is writable
3. Check embedding model is configured in DB-GPT

### SQL accuracy not improving
1. Add more SQL examples for your specific query patterns
2. Add documentation for business terms and column meanings
3. Increase `n_results_sql` for more example context

### Performance issues
1. Reduce `max_context_tokens` if prompts are too large
2. Lower `n_results_*` values to reduce retrieval time
3. Consider using Milvus for larger deployments (future release)

## Next Steps

- Add business documentation for better term understanding
- Train with historical successful queries
- Fine-tune top-k settings for your use case
