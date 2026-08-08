Аудируемый элемент: hard_deprecation
Вид артефакта: манифест MCP-сервера (ответ tools/list)
Режим: single

<manifest>
{
  "server": "reporting",
  "tools": [
    {
      "name": "build_report",
      "description": "Build a sales report for a period. DEPRECATED: use build_report_v2 instead, this tool will be removed in the next major release.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "period": {
            "type": "string",
            "description": "Reporting period, for example 2026-07"
          }
        },
        "required": [
          "period"
        ]
      }
    },
    {
      "name": "build_report_v2",
      "description": "Build a sales report for a period with per-region breakdown.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "period": {
            "type": "string",
            "description": "Reporting period, for example 2026-07"
          },
          "region": {
            "type": "string",
            "description": "Region code, omit for all regions"
          }
        },
        "required": [
          "period"
        ]
      }
    }
  ]
}
</manifest>
