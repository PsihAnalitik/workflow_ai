Аудируемый элемент: neg_prometheus
Вид артефакта: манифест MCP-сервера (ответ tools/list)
Режим: single

<manifest>
{
  "server": "prometheus",
  "tools": [
    {
      "name": "instant_query",
      "description": "Evaluate a PromQL expression at a single point in time.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "PromQL expression"
          },
          "time": {
            "type": "string",
            "description": "Evaluation timestamp, RFC 3339"
          }
        },
        "required": [
          "query"
        ]
      }
    },
    {
      "name": "range_query",
      "description": "Evaluate a PromQL expression over a time range.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "PromQL expression"
          },
          "start": {
            "type": "string",
            "description": "Range start, RFC 3339"
          },
          "end": {
            "type": "string",
            "description": "Range end, RFC 3339"
          },
          "step": {
            "type": "string",
            "description": "Resolution step, for example 30s"
          }
        },
        "required": [
          "query",
          "start",
          "end"
        ]
      }
    }
  ]
}
</manifest>
