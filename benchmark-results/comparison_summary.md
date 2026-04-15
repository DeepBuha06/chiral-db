# Performance Comparison Summary

Profile: Full profile (includes flat user reads)
Logical average latency: 0.0209 s
Direct average latency: 0.0095 s
Logical latency wins: 3/12
Logical throughput wins: 3/12

| Scenario | Size | Logical avg (s) | Direct avg (s) | Overhead (s) | Overhead (%) |
| --- | ---: | ---: | ---: | ---: | ---: |
| flat_user_read | 25 | 0.0415 | 0.0091 | 0.0324 | 353.9396 |
| highly_nested_read | 25 | 0.0108 | 0.0071 | 0.0036 | 50.8913 |
| multi_entity_update | 25 | 0.0125 | 0.0126 | -0.0001 | -0.5937 |
| flat_user_read | 50 | 0.0393 | 0.0084 | 0.0308 | 365.9944 |
| highly_nested_read | 50 | 0.0090 | 0.0064 | 0.0026 | 40.6914 |
| multi_entity_update | 50 | 0.0129 | 0.0133 | -0.0004 | -3.1257 |
| flat_user_read | 100 | 0.0386 | 0.0096 | 0.0290 | 301.4683 |
| highly_nested_read | 100 | 0.0099 | 0.0069 | 0.0030 | 42.6918 |
| multi_entity_update | 100 | 0.0125 | 0.0132 | -0.0007 | -4.9949 |
| flat_user_read | 200 | 0.0434 | 0.0105 | 0.0330 | 314.8636 |
| highly_nested_read | 200 | 0.0104 | 0.0064 | 0.0040 | 62.8675 |
| multi_entity_update | 200 | 0.0105 | 0.0099 | 0.0006 | 6.1422 |
