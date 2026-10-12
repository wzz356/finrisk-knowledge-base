# 原字节、文本与坐标
原件SHA对read_bytes所得字节计算；UTF-8严格解码，有BOM仅移除解码后的BOM，原字节仍保存。
保留CRLF/LF和所有实际换行，不使用read_text的换行归一。文本SHA对full_text.encode('utf-8')计算，未必等于原件SHA。
证据使用Unicode codepoint半开区间[start,end)，start/end必须真实整数且非bool。
引文连续逐字；重复引文枚举含重叠的全部命中，再用相邻锚点消歧。缺失或多命中不得模糊修成verified。
证据定位、语义支持与人审三个状态独立。PDF页码仅在真实查看后记录。
文书text_id按官方file_id与版本定义；旧源版本不覆盖。
对应教材：回源审核与只增不改的证据层，第92–93页。
