# 剩余23份日期及连带处罚引文独立核查

名单严格取date_binding_verification.json中status!=pass的23份。逐份读取quality_common.get(file_id)返回的完整source和原草案。原source和历史稿不改；只写独立content_repair。原日期和原引文原样保存在changes及confirmed_findings的historical_values。完整日期仅采用文书落款或“作出处罚决定的日期”，不采用文号年份、发布日期、业务日期。所有updated_draft保持candidate/pending。

23份均不在early30_overlays中，未发生标签继承覆盖。其余事实保持；F005913因冻结校验暴露异主体处罚引文，同时按具名条目修正两位个人引文和其coverage。

## F001901 — PASS
完整source字符数：550；text SHA：`837af20305f3f0ddde6c8ce2ca0b651dedb21f0e1808dc6e07d514c2f27ab3fc`。

主体：tianan_anhui_false_expenses；处罚决定日期为2012年10月30日。
历史值：`{"penalty_date":"2012年12月31日","penalty_date_quote":"                                          二○一二年十月三十日\n"}`
```text
二○一二年十月三十日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F003266 — PASS
完整source字符数：347；text SHA：`2639bae9b7173f03e996edff93f8233144a366910078d8b7403b048ff3bf414f`。

主体：party_003266；处罚决定日期为2009年7月27日。
历史值：`{"penalty_date":"手机扫一扫打开此页","penalty_date_quote":"手机扫一扫打开此页\n"}`
```text
二○○九年七月二十七日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F004182 — PASS
完整source字符数：397；text SHA：`e0dce12a169f6c0cd2357ef8ef45752d2a3d2d785fd12de178642a34765997a2`。

主体：china_life_liping；完整处罚决定日期不能确认，日期和日期引文改为null，并明确unknown。
历史值：`{"penalty_date":"2025年","penalty_date_quote":"(黔东南金罚决字〔2025〕41-42号、47号)\n"}`
```text
国家金融监督管理总局黔东南监管分局行政处罚信息公开表
(黔东南金罚决字〔2025〕41-42号、47号)
序号
当事人名称
行政处罚决定书文
号
主要违法违规行为
行政处罚内容
作出决定机关
1
中国人寿保
险股份有限
公司黎平支
公司
黔东南金罚决字
〔2025〕41号
以不正当竞争行为扰乱市场
秩序
罚款5万元
国家金融监督
管理总局黔东
南监管分局
2
严三玲(时任
中国人寿保
险股份有限
公司黎平支
公司团险部
经理)
黔东南金罚决字
〔2025〕42号
以不正当竞争行为扰乱市场
秩序
警告并罚款1万元
国家金融监督
管理总局黔东
南监管分局
3
吴庆文(时任
中国人寿保
险股份有限
公司黎平支
公司团体业
务部市场拓
展岗人员)
黔东南金罚决字
〔2025〕47号
以不正当竞争行为扰乱市场
秩序
警告并罚款2万元
国家金融监督
管理总局黔东
南监管分局
手机扫一扫打开此页
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

主体：yan_sanling；完整处罚决定日期不能确认，日期和日期引文改为null，并明确unknown。
历史值：`{"penalty_date":"2025年","penalty_date_quote":"(黔东南金罚决字〔2025〕41-42号、47号)\n"}`
```text
国家金融监督管理总局黔东南监管分局行政处罚信息公开表
(黔东南金罚决字〔2025〕41-42号、47号)
序号
当事人名称
行政处罚决定书文
号
主要违法违规行为
行政处罚内容
作出决定机关
1
中国人寿保
险股份有限
公司黎平支
公司
黔东南金罚决字
〔2025〕41号
以不正当竞争行为扰乱市场
秩序
罚款5万元
国家金融监督
管理总局黔东
南监管分局
2
严三玲(时任
中国人寿保
险股份有限
公司黎平支
公司团险部
经理)
黔东南金罚决字
〔2025〕42号
以不正当竞争行为扰乱市场
秩序
警告并罚款1万元
国家金融监督
管理总局黔东
南监管分局
3
吴庆文(时任
中国人寿保
险股份有限
公司黎平支
公司团体业
务部市场拓
展岗人员)
黔东南金罚决字
〔2025〕47号
以不正当竞争行为扰乱市场
秩序
警告并罚款2万元
国家金融监督
管理总局黔东
南监管分局
手机扫一扫打开此页
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

主体：wu_qingwen；完整处罚决定日期不能确认，日期和日期引文改为null，并明确unknown。
历史值：`{"penalty_date":"2025年","penalty_date_quote":"(黔东南金罚决字〔2025〕41-42号、47号)\n"}`
```text
国家金融监督管理总局黔东南监管分局行政处罚信息公开表
(黔东南金罚决字〔2025〕41-42号、47号)
序号
当事人名称
行政处罚决定书文
号
主要违法违规行为
行政处罚内容
作出决定机关
1
中国人寿保
险股份有限
公司黎平支
公司
黔东南金罚决字
〔2025〕41号
以不正当竞争行为扰乱市场
秩序
罚款5万元
国家金融监督
管理总局黔东
南监管分局
2
严三玲(时任
中国人寿保
险股份有限
公司黎平支
公司团险部
经理)
黔东南金罚决字
〔2025〕42号
以不正当竞争行为扰乱市场
秩序
警告并罚款1万元
国家金融监督
管理总局黔东
南监管分局
3
吴庆文(时任
中国人寿保
险股份有限
公司黎平支
公司团体业
务部市场拓
展岗人员)
黔东南金罚决字
〔2025〕47号
以不正当竞争行为扰乱市场
秩序
警告并罚款2万元
国家金融监督
管理总局黔东
南监管分局
手机扫一扫打开此页
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F004229 — PASS
完整source字符数：514；text SHA：`866b2a1f425b1800cb73c49903b0673943f02fedcdbc07455c10bd98ca4f601f`。

主体：sunshine_xinzhou；处罚决定日期为2025年11月5日。
历史值：`{"penalty_date":"2025年11月5日","penalty_date_quote":"责令改\n正,处16\n万元罚\n款\n"}`
```text
2025年
11月5日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。；F004229日期仅明确出现在机构行，个人空白行未外推。

## F005090 — PASS
完整source字符数：381；text SHA：`a133997abc611bbdfba851db316d174b64e13f7d6389790341043d1f0fd118af`。

主体：pingan_jilin_chaoyang；完整处罚决定日期不能确认，日期和日期引文改为null，并明确unknown。
历史值：`{"penalty_date":"2024年","penalty_date_quote":"行政处罚信息公示表(吉金罚决字〔2024〕125号-127号)\n"}`
```text
行政处罚信息公示表(吉金罚决字〔2024〕125号-127号)
序
号
当事人名
称
行政处罚决定书
文号
主要违法违规行为
行政处罚
内容
作出决定
机关
1
中国平安
人寿保险
股份有限
公司吉林
分公司朝
阳营销服
务部
吉金罚决字
〔2024〕125号
对销售人员管理不
到位
警告并罚
款1万元
吉林金融
监管局
2
孙继旭
(时任中
国平安人
寿保险股
份有限公
司吉林分
公司朝阳
营销服务
部区拓五
区负责人
)
吉金罚决字
〔2024〕126号
对销售人员管理不
到位
警告并罚
款5000元
吉林金融
监管局
3
刘冬艳
(时任中
国平安人
寿保险股
份有限公
司吉林分
公司朝阳
营销服务
部销售人
员
)
吉金罚决字
〔2024〕127号
给予投保人保险合
同约定以外的利益
警告并罚
款5000元
吉林金融
监管局
手机扫一扫打开此页
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

主体：sun_jixu；完整处罚决定日期不能确认，日期和日期引文改为null，并明确unknown。
历史值：`{"penalty_date":"2024年","penalty_date_quote":"行政处罚信息公示表(吉金罚决字〔2024〕125号-127号)\n"}`
```text
行政处罚信息公示表(吉金罚决字〔2024〕125号-127号)
序
号
当事人名
称
行政处罚决定书
文号
主要违法违规行为
行政处罚
内容
作出决定
机关
1
中国平安
人寿保险
股份有限
公司吉林
分公司朝
阳营销服
务部
吉金罚决字
〔2024〕125号
对销售人员管理不
到位
警告并罚
款1万元
吉林金融
监管局
2
孙继旭
(时任中
国平安人
寿保险股
份有限公
司吉林分
公司朝阳
营销服务
部区拓五
区负责人
)
吉金罚决字
〔2024〕126号
对销售人员管理不
到位
警告并罚
款5000元
吉林金融
监管局
3
刘冬艳
(时任中
国平安人
寿保险股
份有限公
司吉林分
公司朝阳
营销服务
部销售人
员
)
吉金罚决字
〔2024〕127号
给予投保人保险合
同约定以外的利益
警告并罚
款5000元
吉林金融
监管局
手机扫一扫打开此页
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

主体：liu_dongyan；完整处罚决定日期不能确认，日期和日期引文改为null，并明确unknown。
历史值：`{"penalty_date":"2024年","penalty_date_quote":"行政处罚信息公示表(吉金罚决字〔2024〕125号-127号)\n"}`
```text
行政处罚信息公示表(吉金罚决字〔2024〕125号-127号)
序
号
当事人名
称
行政处罚决定书
文号
主要违法违规行为
行政处罚
内容
作出决定
机关
1
中国平安
人寿保险
股份有限
公司吉林
分公司朝
阳营销服
务部
吉金罚决字
〔2024〕125号
对销售人员管理不
到位
警告并罚
款1万元
吉林金融
监管局
2
孙继旭
(时任中
国平安人
寿保险股
份有限公
司吉林分
公司朝阳
营销服务
部区拓五
区负责人
)
吉金罚决字
〔2024〕126号
对销售人员管理不
到位
警告并罚
款5000元
吉林金融
监管局
3
刘冬艳
(时任中
国平安人
寿保险股
份有限公
司吉林分
公司朝阳
营销服务
部销售人
员
)
吉金罚决字
〔2024〕127号
给予投保人保险合
同约定以外的利益
警告并罚
款5000元
吉林金融
监管局
手机扫一扫打开此页
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F005723 — PASS
完整source字符数：258；text SHA：`2d3a8cd38cb51fe44193bfffa13a3e9141cb8f2c0536390f8eccf22548463504`。

主体：f005723_case；处罚决定日期为2024年8月15日。
历史值：`{"penalty_date":"2024-8月-5日","penalty_date_quote":"2024年8月15日"}`
```text
2024年8月15日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F005777 — PASS
完整source字符数：323；text SHA：`404cd185203f9567f69426b29ada9f5cee7bdfb256b3a5e5d35c2ca6b6dc4233`。

主体：f005777_case；处罚决定日期为2024年8月8日。
历史值：`{"penalty_date":"2024-8月-日","penalty_date_quote":"2024年8月8日"}`
```text
2024年8月8日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F005845 — PASS
完整source字符数：247；text SHA：`0b9fec1b749e01d860eccbdc16aed5ee67cfbbf2d6b56ec05c9bd2def90ed8da`。

主体：f005845_case；处罚决定日期为2024年7月29日。
历史值：`{"penalty_date":"2024-7月-9日","penalty_date_quote":"2024年7月29日"}`
```text
2024年7月29日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F005913 — PASS
完整source字符数：350；text SHA：`881d693ebb6c31f5db2de3cf1b1eaf4fe69c60fa4d0b8cf27e438c4871b9fc7a`。

主体：pingan_shanghai_callcenter；处罚决定日期为2024年7月16日。
历史值：`{"penalty_date":"2024年7月16日","penalty_date_quote":"作出处罚决定的日期\n"}`
```text
2024年7月16日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

主体：yang_yanhong；处罚决定日期为2024年7月16日。
历史值：`{"penalty_date":"2024年7月16日","penalty_date_quote":"作出处罚决定的日期\n"}`
```text
2024年7月16日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

主体：zhu_qikui；处罚决定日期为2024年7月16日。
历史值：`{"penalty_date":"2024年7月16日","penalty_date_quote":"作出处罚决定的日期\n"}`
```text
2024年7月16日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

主体：pingan_shanghai_callcenter；将处罚与摘要引文绑定本主体；机构15万元、杨艳红4万元、朱起魁4万元金额保持原值。
历史值：`{"penalties":[{"amount_quote":"一、对中国平安人寿保险股份有限\n公司上海电话销售中心罚款15万元\n","amount_yuan":150000,"basis_quote":"一、对中国平安人寿保险股份有限\n公司上海电话销售中心罚款15万元\n","currency":null,"currency_quote":null,"type":"罚款"}],"case_summary_quotes":["欺骗投保人\n","行政处罚决定\n一、对中国平安人寿保险股份有限\n"]}`
```text
一、对中国平安人寿保险股份有限
公司上海电话销售中心罚款15万元
```
限制：原文没有把欺骗投保人具体行为逐人分配，不认定个人亲自实施。

主体：yang_yanhong；将处罚与摘要引文绑定本主体；机构15万元、杨艳红4万元、朱起魁4万元金额保持原值。
历史值：`{"penalties":[{"amount_quote":null,"amount_yuan":null,"basis_quote":"三、对朱起魁警告并处罚款4万元\n","currency":null,"currency_quote":null,"type":"警告"},{"amount_quote":"三、对朱起魁警告并处罚款4万元\n","amount_yuan":40000,"basis_quote":"三、对朱起魁警告并处罚款4万元\n","currency":null,"currency_quote":null,"type":"罚款"}],"case_summary_quotes":["欺骗投保人\n","公司上海电话销售中心罚款15万元\n"]}`
```text
二、对杨艳红警告并处罚款4万元
```
限制：原文没有把欺骗投保人具体行为逐人分配，不认定个人亲自实施。

主体：zhu_qikui；将处罚与摘要引文绑定本主体；机构15万元、杨艳红4万元、朱起魁4万元金额保持原值。
历史值：`{"penalties":[{"amount_quote":null,"amount_yuan":null,"basis_quote":"二、对杨艳红警告并处罚款4万元\n","currency":null,"currency_quote":null,"type":"警告"},{"amount_quote":"二、对杨艳红警告并处罚款4万元\n","amount_yuan":40000,"basis_quote":"二、对杨艳红警告并处罚款4万元\n","currency":null,"currency_quote":null,"type":"罚款"}],"case_summary_quotes":["欺骗投保人\n","二、对杨艳红警告并处罚款4万元\n"]}`
```text
三、对朱起魁警告并处罚款4万元
```
限制：原文没有把欺骗投保人具体行为逐人分配，不认定个人亲自实施。

## F006165 — PASS
完整source字符数：272；text SHA：`42f5954ba18c65d07a88a445cee0d0c25bd8ead5c48449acad96f10f9cd6283e`。

主体：person；处罚决定日期为2024年6月7日。
历史值：`{"penalty_date":"行政处罚决定","penalty_date_quote":"行政处罚决定\n"}`
```text
2024年6月7日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F006204 — PASS
完整source字符数：306；text SHA：`d03daf5ab56f20d9887f50718fc9778ffab32e81b0cbf69f8da51164cdad75fd`。

主体：f006204_company；处罚决定日期为2024年6月11日。
历史值：`{"penalty_date":"2024-6月-1日","penalty_date_quote":"2024年6月11日"}`
```text
2024年6月11日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

主体：f006204_person；处罚决定日期为2024年6月11日。
历史值：`{"penalty_date":"2024-6月-1日","penalty_date_quote":"2024年6月11日"}`
```text
2024年6月11日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F006276 — PASS
完整source字符数：244；text SHA：`ff53ec00a1e14b6fcf360e6dc95af4ae54a1b2e02d5bd6aea928ddea9005c408`。

主体：person；处罚决定日期为2024年5月29日。
历史值：`{"penalty_date":"作出处罚决定的","penalty_date_quote":"作出处罚决定的\n"}`
```text
2024年5月29日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F006302 — PASS
完整source字符数：221；text SHA：`7b829d83aaae3f73d33c52f2fc00204e92341abe1c8f829d0945da7e008a895b`。

主体：institution；处罚决定日期为2024年5月28日。
历史值：`{"penalty_date":"机关名称","penalty_date_quote":"机关名称\n"}`
```text
2024年5月28日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F006406 — PASS
完整source字符数：302；text SHA：`5b600ba5f88a68166905dc23e09efe29841171ae8c37a6b0bc923a2da07e8f15`。

主体：f006406_person；处罚决定日期为2024年5月15日。
历史值：`{"penalty_date":"2024-5月-5日","penalty_date_quote":"2024年5月15日"}`
```text
2024年5月15日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F006627 — PASS
完整source字符数：276；text SHA：`0983963d62b1f062ab772e1c6453b2e8bf58628d4ec63d70028253508d99c9f5`。

主体：subject；处罚决定日期为2024年4月21日。
历史值：`{"penalty_date":"行政处罚决定","penalty_date_quote":"行政处罚决定\n"}`
```text
2024年4月21日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F006648 — PASS
完整source字符数：281；text SHA：`f448ed2f44cca566e4de2164e9c8679c12c2e525bd9a5da73ea63aeca6308f55`。

主体：f006648_inst；处罚决定日期为2024年4月18日。
历史值：`{"penalty_date":"2024-4月-8日","penalty_date_quote":"2024年4月18日"}`
```text
2024年4月18日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F006813 — PASS
完整source字符数：254；text SHA：`2392118a8375d64ad04bb14cc9d0489170197f519f63a7df598815bcd15d690a`。

主体：f006813_inst；处罚决定日期为2024年3月29日。
历史值：`{"penalty_date":"2024-3月-9日","penalty_date_quote":"2024年3月29日"}`
```text
2024年3月29日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F008100 — PASS
完整source字符数：231；text SHA：`11d0f27d71680560dddc472efd5968d924edc7e96a90aef5a3228728d5c21bf1`。

主体：f008100_inst；处罚决定日期为2023年12月1日。
历史值：`{"penalty_date":"2023-12-1日","penalty_date_quote":"2023年12月1日"}`
```text
2023年12月1日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F008655 — PASS
完整source字符数：263；text SHA：`4e469d5b8a87f410c6c3b5490daf612c2a36f37730e4932526d7e73bcc7631e1`。

主体：f008655_1；处罚决定日期为2023年8月31日。
历史值：`{"penalty_date":"2023-8月-1日","penalty_date_quote":"2023年8月31日"}`
```text
2023年8月31日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F008668 — PASS
完整source字符数：274；text SHA：`e3acc97060a64f9b6fcc1c4f0e605b13b87cfc01ce99e06809bc0533c83e9b3f`。

主体：f008668_1；处罚决定日期为2023年8月28日。
历史值：`{"penalty_date":"2023-8月-8日","penalty_date_quote":"2023年8月28日"}`
```text
2023年8月28日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

主体：f008668_2；处罚决定日期为2023年8月28日。
历史值：`{"penalty_date":"2023-8月-8日","penalty_date_quote":"2023年8月28日"}`
```text
2023年8月28日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F008770 — PASS
完整source字符数：247；text SHA：`d72592af09fbef154ce5ccb85a4f092ebb71f9420b47eb6f9e1b3f39ba561852`。

主体：f008770_1；处罚决定日期为2023年8月10日。
历史值：`{"penalty_date":"2023-8月-0日","penalty_date_quote":"2023年8月10日"}`
```text
2023年8月10日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F008775 — PASS
完整source字符数：218；text SHA：`cc808003e5ea3832fcea22453d1657b35eb9cacf6f49ff60c99f2d3d258cf569`。

主体：f008775_1；处罚决定日期为2023年8月10日。
历史值：`{"penalty_date":"2023-8月-0日","penalty_date_quote":"2023年8月10日"}`
```text
2023年8月10日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## F009101 — PASS
完整source字符数：767；text SHA：`ebcedffbc6c71b189eff360211a915758c56695e737805a9dc93afbd37a351ca`。

主体：f009101_1；处罚决定日期为2023年6月30日。
历史值：`{"penalty_date":"2023-6月-0日","penalty_date_quote":"2023年6月30日"}`
```text
2023年6月30日
```
限制：此处仅核定处罚决定日期，不能用于推断业务发生期间。

## 实际验证
```json
[
  {
    "file_id": "F001901",
    "status": "pass",
    "validation": {
      "requires_review": false,
      "reasons": [],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 32,
      "quote_spans_checked": 32,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "tianan_anhui_false_expenses",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F003266",
    "status": "pass",
    "validation": {
      "requires_review": false,
      "reasons": [],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 26,
      "quote_spans_checked": 26,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "party_003266",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F004182",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "multiple_decisions",
        "multiple_penalized_subjects",
        "non_fine_monetary_amount_requires_review",
        "personal_responsibility_link"
      ],
      "cases": 3,
      "behaviors": 3,
      "quote_fields_checked": 89,
      "quote_spans_checked": 177,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "china_life_liping",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yan_sanling",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "wu_qingwen",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F004229",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "multiple_penalized_subjects"
      ],
      "cases": 4,
      "behaviors": 5,
      "quote_fields_checked": 160,
      "quote_spans_checked": 272,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "sunshine_xinzhou",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "lu_wenchen",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "du_fukang",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yao_huiming",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F005090",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "multiple_decisions",
        "multiple_penalized_subjects",
        "non_fine_monetary_amount_requires_review",
        "personal_responsibility_link"
      ],
      "cases": 3,
      "behaviors": 3,
      "quote_fields_checked": 82,
      "quote_spans_checked": 138,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "pingan_jilin_chaoyang",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "sun_jixu",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "liu_dongyan",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F005723",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 43,
      "quote_spans_checked": 47,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f005723_case",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F005777",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 3,
      "quote_fields_checked": 69,
      "quote_spans_checked": 73,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f005777_case",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F005845",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 43,
      "quote_spans_checked": 47,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f005845_case",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F005913",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "multiple_penalized_subjects"
      ],
      "cases": 3,
      "behaviors": 3,
      "quote_fields_checked": 78,
      "quote_spans_checked": 78,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "pingan_shanghai_callcenter",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yang_yanhong",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhu_qikui",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F006165",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "penalty_amount_ambiguous_or_unparsed",
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 40,
      "quote_spans_checked": 42,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "person",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F006204",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "multiple_penalized_subjects",
        "personal_responsibility_link"
      ],
      "cases": 2,
      "behaviors": 2,
      "quote_fields_checked": 67,
      "quote_spans_checked": 74,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f006204_company",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "f006204_person",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F006276",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "penalty_amount_ambiguous_or_unparsed",
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 38,
      "quote_spans_checked": 38,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "person",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F006302",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "penalty_amount_ambiguous_or_unparsed"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 36,
      "quote_spans_checked": 36,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "institution",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F006406",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 2,
      "quote_fields_checked": 62,
      "quote_spans_checked": 69,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f006406_person",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F006627",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "penalty_amount_ambiguous_or_unparsed",
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 40,
      "quote_spans_checked": 42,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "subject",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F006648",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "aggregate_or_split_penalty"
      ],
      "cases": 1,
      "behaviors": 2,
      "quote_fields_checked": 57,
      "quote_spans_checked": 64,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f006648_inst",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F006813",
    "status": "pass",
    "validation": {
      "requires_review": false,
      "reasons": [],
      "cases": 1,
      "behaviors": 2,
      "quote_fields_checked": 59,
      "quote_spans_checked": 67,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f006813_inst",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F008100",
    "status": "pass",
    "validation": {
      "requires_review": false,
      "reasons": [],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 44,
      "quote_spans_checked": 52,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f008100_inst",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F008655",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 42,
      "quote_spans_checked": 48,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f008655_1",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F008668",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "multiple_penalized_subjects",
        "penalty_amount_ambiguous_or_unparsed"
      ],
      "cases": 2,
      "behaviors": 2,
      "quote_fields_checked": 67,
      "quote_spans_checked": 71,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f008668_1",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "f008668_2",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F008770",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 44,
      "quote_spans_checked": 49,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f008770_1",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F008775",
    "status": "pass",
    "validation": {
      "requires_review": false,
      "reasons": [],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 40,
      "quote_spans_checked": 46,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f008775_1",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F009101",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "aggregate_or_split_penalty",
        "personal_responsibility_link"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 50,
      "quote_spans_checked": 52,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "f009101_1",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  }
]
```

已完成23/23；通过23；candidate/pending；人工批准0。
