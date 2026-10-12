# 独立内容审核与新增内容修订

独立读取9份file_index绑定的完整source：F003945、F003958、F003989、F004695、F003992、F003693、F007059、F007506、F007742。核对主体、责任角色、逐案由映射、处罚与金额归属；未调用API、未读盲验或凭据。本文为模型独立核查，所有草案保持candidate/pending，人工批准数为0。

## Priority20五修稿核查

五份既有修稿通过本次内容复核。仅原文主体行直接列明违法行为时接受direct_person_violation；组表明确“及相关责任人员/责任人”时仅接受responsible_person，不把全部组案由分配为每人实施事实。召回候选标签始终不能替代事实或责任认定。

### F003945 — PASS
吴臻宇、陈智川个人行各自列明给予投保人合同外利益，赵宁个人行列明编制虚假业务财务资料。三人角色/动作/摘要修订有直接行依据；未把吴丽红、许美晶或空白相邻行案由扩展为其他人员行为。利益形式与虚假资料机制未补写。

全文字符数：1049；原草案SHA：`919db872e003786084958365a2ffc8778e417bf4ed8b2b34b4803d40f61057e8`；源文SHA：`d6417ce43985026c6fb1aac0d14f2a0db569f01f2f5313b9de219d2d54268707`。

证据 F003945-P1（source连续区间 199..282；wu_zhenyu）：
```text
吴臻宇(时任太
平人寿保险有
限公司济南中
心支公司个人
业务部经理)
鲁金罚决字
〔2026〕31号
给予投保人保
险合同约定以
外的其他利益
警告并罚
款1万元
```

证据 F003945-P2（source连续区间 303..386；chen_zhichuan）：
```text
陈智川(时任太
平人寿保险有
限公司济南中
心支公司个人
业务部经理)
鲁金罚决字
〔2026〕32号
给予投保人保
险合同约定以
外的其他利益
警告并罚
款2万元
```

证据 F003945-P3（source连续区间 523..596；zhao_ning）：
```text
赵宁(时任太平
人寿保险有限
公司泰安中心
支公司银行保
险部经理)
鲁金罚决字
〔2026〕34号
编制虚假业务
财务资料
警告并罚
款3万元
```

### F003958 — PASS
第9条将侯丽珠、殷鹏飞、张梦瑶列为个人代理人并共同列明利用保险业务谋不正当利益；direct_person_violation可在该共同明列事项范围内接受，具体分工、获利形式未知。合计0.3万元仍为三人组额，个人金额未分摊。

全文字符数：1213；原草案SHA：`a7734cbb9c6fe5ed296254e7bacd6a7a942ef1689ca96e01bf83fc901bc98533`；源文SHA：`b7d20807096892a6ccebf4a6aeaed19aca0f0fda3351cc8e0ee5ecd91cc4d263`。

证据 F003958-P1（source连续区间 1090..1184；hou）：
```text
富德生命人
寿保险股份
有限公司合
肥中心支公
司个人代理
人侯丽珠、
殷鹏飞、张
梦瑶
利用保险业务为个
人谋取不正当利益
对侯丽珠、殷
鹏飞、张梦瑶
警告并处罚款
合计0.3万
元。
```

证据 F003958-P2（source连续区间 1090..1184；yin）：
```text
富德生命人
寿保险股份
有限公司合
肥中心支公
司个人代理
人侯丽珠、
殷鹏飞、张
梦瑶
利用保险业务为个
人谋取不正当利益
对侯丽珠、殷
鹏飞、张梦瑶
警告并处罚款
合计0.3万
元。
```

证据 F003958-P3（source连续区间 1090..1184；zhang_mengyao）：
```text
富德生命人
寿保险股份
有限公司合
肥中心支公
司个人代理
人侯丽珠、
殷鹏飞、张
梦瑶
利用保险业务为个
人谋取不正当利益
对侯丽珠、殷
鹏飞、张梦瑶
警告并处罚款
合计0.3万
元。
```

### F003989 — PASS
华安、阳光、永诚三组明示“及相关责任人员”并在本组列出姓名，可确认相关责任人身份。65条行为记录角色修订为responsible_person，而动作保持null、标签仍inferred/document_related，限制明确未逐人分配事项。个人组额84万元、18万元、18万元均未分摊。

全文字符数：489；原草案SHA：`6673b09f5970160119c3315d03e587ab5452126ddf659500b555cdcbb229203a`；源文SHA：`4d55eb4a9b9320387c8febfa3fd4a608056836143205520448fdb1dfc41a8830`。

证据 F003989-P1（source连续区间 0..489；hua_person）：
```text
国家金融监督管理总局行政处罚信息公示列表
〔2026〕号
序号
当事人
名称
主要违法违规
行为
行政处罚内容
作出决定
机关
1
华安财产保
险股份有限
公司及相关
责任人员
未按照规定使用经批准
或备案的保险条款、费
率,报送数据不准确,跨
区域开展业务等。
对华安财产保险股份有限公
司警告并罚款386万元,对山
东分公司罚款60万元,对福
建分公司罚款35万元。
对袁秀奇、吴向华、朱军
威、廖飞舟、陈巍巍、王
巧、王璐娟、余华、赵忠
恩、凤奕、张玉华、鲁志
豪、徐沛警告并罚款共计84
万元。
金融监管
总局
2
阳光保险集
团股份有限
公司及相关
责任人员
关联交易管理不到位,
偿付能力报告数据不准
确等。
对阳光保险集团股份有限公
司罚款140万元。
对张艳秋、张秀美警告并罚
款共计18万元。
金融监管
总局
3
永诚保险资
产管理有限
公司及相关
责任人员
资产管理业务开展不规
范,关联交易管理不规
范,财务数据不准确
等。
对永诚保险资产管理有限公
司罚款120万元。
对王凡、张岩姝、王群警告
并罚款共计18万元。
金融监管
总局
手机扫一扫打开此页
```

证据 F003989-P2（source连续区间 0..489；yang_person）：
```text
国家金融监督管理总局行政处罚信息公示列表
〔2026〕号
序号
当事人
名称
主要违法违规
行为
行政处罚内容
作出决定
机关
1
华安财产保
险股份有限
公司及相关
责任人员
未按照规定使用经批准
或备案的保险条款、费
率,报送数据不准确,跨
区域开展业务等。
对华安财产保险股份有限公
司警告并罚款386万元,对山
东分公司罚款60万元,对福
建分公司罚款35万元。
对袁秀奇、吴向华、朱军
威、廖飞舟、陈巍巍、王
巧、王璐娟、余华、赵忠
恩、凤奕、张玉华、鲁志
豪、徐沛警告并罚款共计84
万元。
金融监管
总局
2
阳光保险集
团股份有限
公司及相关
责任人员
关联交易管理不到位,
偿付能力报告数据不准
确等。
对阳光保险集团股份有限公
司罚款140万元。
对张艳秋、张秀美警告并罚
款共计18万元。
金融监管
总局
3
永诚保险资
产管理有限
公司及相关
责任人员
资产管理业务开展不规
范,关联交易管理不规
范,财务数据不准确
等。
对永诚保险资产管理有限公
司罚款120万元。
对王凡、张岩姝、王群警告
并罚款共计18万元。
金融监管
总局
手机扫一扫打开此页
```

证据 F003989-P3（source连续区间 0..489；yong_person）：
```text
国家金融监督管理总局行政处罚信息公示列表
〔2026〕号
序号
当事人
名称
主要违法违规
行为
行政处罚内容
作出决定
机关
1
华安财产保
险股份有限
公司及相关
责任人员
未按照规定使用经批准
或备案的保险条款、费
率,报送数据不准确,跨
区域开展业务等。
对华安财产保险股份有限公
司警告并罚款386万元,对山
东分公司罚款60万元,对福
建分公司罚款35万元。
对袁秀奇、吴向华、朱军
威、廖飞舟、陈巍巍、王
巧、王璐娟、余华、赵忠
恩、凤奕、张玉华、鲁志
豪、徐沛警告并罚款共计84
万元。
金融监管
总局
2
阳光保险集
团股份有限
公司及相关
责任人员
关联交易管理不到位,
偿付能力报告数据不准
确等。
对阳光保险集团股份有限公
司罚款140万元。
对张艳秋、张秀美警告并罚
款共计18万元。
金融监管
总局
3
永诚保险资
产管理有限
公司及相关
责任人员
资产管理业务开展不规
范,关联交易管理不规
范,财务数据不准确
等。
对永诚保险资产管理有限公
司罚款120万元。
对王凡、张岩姝、王群警告
并罚款共计18万元。
金融监管
总局
手机扫一扫打开此页
```

### F004695 — PASS
18条修订行为均有个人主体行直接列明对应违法行为：崔昊、张金龙、谭春艳3项、高凛、李方、高太文、姜想象、张科、黄世荣、刘再辉2项、秦智勇、张恩豪、刘安华、戴伟、何珂。刘再辉仅限“公司治理混乱部分问题”。case unknowns删去了具体参与/机制未载，但每条behavior summary、regulatory_finding及标签limitations继续明确“具体实施机制未载”，未实际补写机制。金额、文号、日期、机构个人处罚字段未改。

全文字符数：1797；原草案SHA：`070210ce1a7839838fcadc981d4e93ff390238e44a3171306a3de4a37ab6322c`；源文SHA：`0c1ce84c101b305dba717ca6579eed164093340e9d1a8610001b746fd94ec73e`。

证据 F004695-P1（source连续区间 643..675；cui）：
```text
崔昊(利宝
保险有限公
司副总经
理)
准备金系统建
设不完善
```

证据 F004695-P2（source连续区间 688..718；zhangjinlong）：
```text
张金龙(利
宝保险有限
公司精算部
准备金系统建
设不完善
```

证据 F004695-P3（source连续区间 763..823；tan）：
```text
谭春艳(利
宝保险有限
公司重庆分
公司总经
理)
虚构保险中介
业务套取费用,
编制虚假财务
资料,内控管理
不规范
```

证据 F004695-P4（source连续区间 763..823；tan）：
```text
谭春艳(利
宝保险有限
公司重庆分
公司总经
理)
虚构保险中介
业务套取费用,
编制虚假财务
资料,内控管理
不规范
```

证据 F004695-P5（source连续区间 763..823；tan）：
```text
谭春艳(利
宝保险有限
公司重庆分
公司总经
理)
虚构保险中介
业务套取费用,
编制虚假财务
资料,内控管理
不规范
```

证据 F004695-P6（source连续区间 839..879；gaolin）：
```text
高凛(利宝
保险有限公
司重庆分公
司综合业务
四部经理)
编制虚假财务
资料
```

证据 F004695-P7（source连续区间 892..933；lifang）：
```text
李方(利宝
保险有限公
司重庆分公
司业务部经
理)
虚构保险中介
业务套取费用
```

证据 F004695-P8（source连续区间 946..994；gaotaiwen）：
```text
高太文(时
任利宝保险
有限公司重
庆分公司综
合业务二部
经理)
虚构保险中介
业务套取费用
```

证据 F004695-P9（source连续区间 1007..1047；jiang）：
```text
姜想象(时
任利宝保险
有限公司永
川中心支公
司总经理)
编制虚假财务
资料
```

证据 F004695-P10（source连续区间 1060..1099；zhangke）：
```text
张科(时任
利宝保险有
限公司永川
中心支公司
总经理)
编制虚假财务
资料
```

证据 F004695-P11（source连续区间 1112..1154；huang）：
```text
黄世荣(利
宝保险有限
公司涪陵中
心支公司总
经理)
虚构保险中介
业务套取费用
```

证据 F004695-P12（source连续区间 1406..1455；liu）：
```text
刘再辉(时
任三峡人寿
保险股份有
限公司董事
会秘书)
编制虚假报
告、公司治理
混乱部分问题
```

证据 F004695-P13（source连续区间 1406..1455；liu）：
```text
刘再辉(时
任三峡人寿
保险股份有
限公司董事
会秘书)
编制虚假报
告、公司治理
混乱部分问题
```

证据 F004695-P14（source连续区间 1471..1527；qin）：
```text
秦智勇(时
任三峡人寿
保险股份有
限公司重庆
分公司团险
业务部万州
业务部经
理)
虚构中介业务
套取费用
```

证据 F004695-P15（source连续区间 1540..1585；zhangenhao）：
```text
张恩豪(时
任三峡人寿
保险股份有
限公司银行
保险部培训
督导岗)
编制虚假财务
资料
```

证据 F004695-P16（source连续区间 1598..1652；liuanhua）：
```text
刘安华〔时
任三峡人寿
保险股份有
限公司重庆
分公司培训
部副经理
(主持工
作)〕
编制虚假财务
资料
```

证据 F004695-P17（source连续区间 1665..1720；daiwei）：
```text
戴伟〔时任
三峡人寿保
险股份有限
公司重庆分
公司银行保
险部副经理
(主持工
作)〕
编制虚假财务
资料
```

证据 F004695-P18（source连续区间 1733..1777；heke）：
```text
何珂(时任
三峡人寿保
险股份有限
公司重庆分
公司总经理
助理)
编制虚假财务
资料
```

### F003992 — PASS
湖北省分公司和武汉市分公司两组都明示“及相关责任人”，可确认50条行为记录所涉人员责任身份。具体动作保持null、标签inferred/document_related且逐人分配仍未知；39万元组额未分摊。武汉组丁信1万元及朱波波、谌宗宸终身禁止进入保险业保持分别原值。

全文字符数：340；原草案SHA：`4480ce3f7c2792f8e9d677ba45db92714b3ff82bbc7421b1bdcc0ad0110b051d`；源文SHA：`a66fb22998df1f5f81d9e9e61f5f3b2f4dff9793ad495b997ca4cd531e487720`。

证据 F003992-P1（source连续区间 0..340；hubei_person_group）：
```text
国家金融监督管理总局湖北监管局
行政处罚信息公开表
序
号
当事人名
称
主要违法违规行为
行政处罚内容
作出决定
机关
1
中国人寿
保险股份
有限公司
湖北省分
公司及相
关责任人
编制虚假资料、利用
开展保险业务为其他
个人牟取不正当利
益、给予投保人保险
合同约定以外的利
益、欺骗投保人
对机构罚款117万
元。对张蔚、张辉、
黄欢、何伟、胡煜、
齐倩玲、秦红、周
凤、尹聪、刘莹、冯
羽警告并罚款共计39
万元。
湖北金融
监管局
2
中国人寿
保险股份
有限公司
武汉市分
公司及相
关责任人
个人保险代理人管理
不到位、欺骗投保人
对机构警告并罚款1
万元。对丁信警告并
罚款1万元,对朱波
波、谌宗宸终身禁止
进入保险业。
湖北金融
监管局
手机扫一扫打开此页
```

证据 F003992-P2（source连续区间 0..340；wuhan_person_group）：
```text
国家金融监督管理总局湖北监管局
行政处罚信息公开表
序
号
当事人名
称
主要违法违规行为
行政处罚内容
作出决定
机关
1
中国人寿
保险股份
有限公司
湖北省分
公司及相
关责任人
编制虚假资料、利用
开展保险业务为其他
个人牟取不正当利
益、给予投保人保险
合同约定以外的利
益、欺骗投保人
对机构罚款117万
元。对张蔚、张辉、
黄欢、何伟、胡煜、
齐倩玲、秦红、周
凤、尹聪、刘莹、冯
羽警告并罚款共计39
万元。
湖北金融
监管局
2
中国人寿
保险股份
有限公司
武汉市分
公司及相
关责任人
个人保险代理人管理
不到位、欺骗投保人
对机构警告并罚款1
万元。对丁信警告并
罚款1万元,对朱波
波、谌宗宸终身禁止
进入保险业。
湖北金融
监管局
手机扫一扫打开此页
```

## 新增四份确认问题与修订

四份均确认内容问题，生成4条独立content_repair overlay，没有与priority20/early30重复。其余所有字段逐值保留，仅下列证据覆盖的引文、金额和关联字段变化。F007742不仅一条引文错误，连带三家机构罚款金额循环错配，按具名条目修正。

### F003693 — CONFIRMED/REPAIRED

证据 F003693-L1；字段：/behaviors/0/finding_quote and its own coverage classification。
原finding_quote仅引保险法依据与10万元处罚，替换为监管对虚开发票、报销套费、直付底薪导致记录不实的连续认定。
限制：只修行为认定引文与相应coverage分类；动作、主体、金额、历史日期以及标签和其余引文均保持原值。
```text
你中心支公司通过保险中介机构虚开手续费发票和报销营业费用套取资金支付手续费,向保险中介机构(汕头瀛安)营销员直接支付工资底薪等行为,导致业务、财务资料未如实记录保险业务事项,
```

### F007059 — CONFIRMED/REPAIRED

证据 F007059-L1；字段：penalties basis_quote/amount_quote and case_summary_quotes。
将错引机构的5000元处罚依据改为肖岚具名处罚条目，金额5000元保持原值。
限制：个人与机构案由对应关系仍未知，不认定亲自收受、指使或给予利益。
```text
三、对肖岚警告并处罚款5000元
```

### F007506 — CONFIRMED/REPAIRED

证据 F007506-L1；字段：penalties basis_quote/amount_quote, case_summary_quotes, matching coverage。
机构警告及10000元罚款应引用机构条目；拆出原误归context的机构处罚，个人处罚仅关联张强。
限制：金额10000元保持原值；其余行为、候选标签、未知责任对应等保持原值。
```text
一、对北京远安保险经纪有限公司处以
警告并罚款1万元
```

### F007742 — CONFIRMED/REPAIRED

证据 F007742-L1；字段：penalties amount_yuan/basis_quote/amount_quote, case_summary_quotes, matching coverage。
中国人寿财产保险股份有限公司贺兰支公司处罚为270000元；按具名处罚对应，而不是按当事人列表序号对应。
限制：罚款主体归属有明确连续依据；三类违法行为仍不能逐主体分配。
```text
五、对中国人寿财产保险股份有限公司贺兰支
公司罚款27万元
```

证据 F007742-L2；字段：penalties amount_yuan/basis_quote/amount_quote, case_summary_quotes, matching coverage。
中国人寿财产保险股份有限公司永宁支公司处罚为150000元；按具名处罚对应，而不是按当事人列表序号对应。
限制：罚款主体归属有明确连续依据；三类违法行为仍不能逐主体分配。
```text
三、对中国人寿财产保险股份有限公司永宁支
公司罚款15万元
```

证据 F007742-L3；字段：penalties amount_yuan/basis_quote/amount_quote, case_summary_quotes, matching coverage。
中国人寿财产保险股份有限公司灵武支公司处罚为80000元；按具名处罚对应，而不是按当事人列表序号对应。
限制：罚款主体归属有明确连续依据；三类违法行为仍不能逐主体分配。
```text
四、对中国人寿财产保险股份有限公司灵武支
公司罚款8万元
```

## 实际验证

四条overlay的base_draft_json_sha256与base_text_sha256逐份等于file_index；updated_draft_json_sha256按canonical JSON重算；confirmed_findings所有source_quote逐字连续匹配全文；通过run_v2.apply_overlays绑定/身份/状态检查。已有五修稿亦重新核对base SHA、updated SHA，并核验处罚、金额、日期、文号、法规字段未改。

冻结compatibility guard结果如下（未放宽规则，产物在content_independent_validation/）：
```json
[
  {
    "file_id": "F003945",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "important_or_critical_unresolved",
        "multiple_decisions",
        "multiple_penalized_subjects"
      ],
      "cases": 10,
      "behaviors": 11,
      "quote_fields_checked": 181,
      "quote_spans_checked": 244,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "tp_jinan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "wu_zhenyu",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "chen_zhichuan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "wu_lihong",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhao_ning",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "tp_taian",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "tp_zibo",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "wang_deming",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "li_jia",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "xu_meijing",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F003958",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "aggregate_or_split_penalty",
        "multiple_penalized_subjects",
        "penalty_amount_ambiguous_or_unparsed",
        "personal_responsibility_link"
      ],
      "cases": 35,
      "behaviors": 64,
      "quote_fields_checked": 774,
      "quote_spans_checked": 1306,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "pa_anhui",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "liu_xinwen",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "tian",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "luo",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "liu_zhen",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "pa_anqing",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "jiang",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "wang_erjin",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "pa_bengbu",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yuan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "xue",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "pa_fuyang",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhao",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "wang_saiyu",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "pa_huangshan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "shi",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "huang_anqiang",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "pa_maanshan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hong",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "huang_xianjin",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "fude_anhui",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "tao_xi",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhang_nan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhou",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "liu_guoqi",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "pei",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "he",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "wang_lei",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "fude_hefei",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "huang_jinju",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "tao_chen",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhao_zhuo",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hou",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yin",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhang_mengyao",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F003989",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "aggregate_or_split_penalty",
        "important_or_critical_unresolved",
        "multiple_penalized_subjects",
        "penalty_amount_ambiguous_or_unparsed",
        "personal_responsibility_link"
      ],
      "cases": 23,
      "behaviors": 82,
      "quote_fields_checked": 1031,
      "quote_spans_checked": 1033,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "hua",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_sd",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_fj",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person1",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person2",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person3",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person4",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person5",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person6",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person7",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person8",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person9",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person10",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person11",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person12",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hua_person13",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yang",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yang_person1",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yang_person2",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yong",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yong_person1",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yong_person2",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yong_person3",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F004695",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "declared_source_issue",
        "multiple_penalized_subjects"
      ],
      "cases": 21,
      "behaviors": 29,
      "quote_fields_checked": 426,
      "quote_spans_checked": 1566,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "liberty",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "chongqing",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "yongchuan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "fuling",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "cui",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhangjinlong",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "tan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "gaolin",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "lifang",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "gaotaiwen",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "jiang",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhangke",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "huang",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "sanxia",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "sxchongqing",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "liu",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "qin",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhangenhao",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "liuanhua",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "daiwei",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "heke",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F003992",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "aggregate_or_split_penalty",
        "important_or_critical_unresolved",
        "multiple_penalized_subjects",
        "penalty_amount_ambiguous_or_unparsed",
        "penalty_amount_unknown_requires_review",
        "personal_responsibility_link"
      ],
      "cases": 16,
      "behaviors": 56,
      "quote_fields_checked": 517,
      "quote_spans_checked": 517,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "life_hubei",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_0",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_1",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_2",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_3",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_4",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_5",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_6",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_7",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_8",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_9",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "hubei_person_10",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "life_wuhan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "ding_xin",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhu_bobo",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "chen_zongchen",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F003693",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "aggregate_or_split_penalty",
        "declared_source_issue",
        "penalty_amount_ambiguous_or_unparsed"
      ],
      "cases": 1,
      "behaviors": 1,
      "quote_fields_checked": 46,
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
          "case_key": "zhonghua_shantou",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F007059",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "multiple_penalized_subjects"
      ],
      "cases": 3,
      "behaviors": 3,
      "quote_fields_checked": 61,
      "quote_spans_checked": 61,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "firm",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "chen_shengquan",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "xiao_lan",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F007506",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "multiple_penalized_subjects"
      ],
      "cases": 2,
      "behaviors": 2,
      "quote_fields_checked": 44,
      "quote_spans_checked": 44,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "firm",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "zhang_qiang",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  },
  {
    "file_id": "F007742",
    "status": "pass",
    "validation": {
      "requires_review": true,
      "reasons": [
        "important_or_critical_unresolved",
        "multiple_penalized_subjects"
      ],
      "cases": 23,
      "behaviors": 23,
      "quote_fields_checked": 457,
      "quote_spans_checked": 475,
      "all_quotes_exact": true,
      "uncovered_tokens": [],
      "compatibility_version": "finrisk-compat-v1",
      "structural_replacements": {
        "name": 1,
        "currency": 1
      },
      "name_checks": [
        {
          "case_key": "subject_1",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_2",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_3",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_4",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_5",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_6",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_7",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_8",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_9",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_10",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_11",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_12",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_13",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_14",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_15",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_16",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_17",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_18",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_19",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_20",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_21",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_22",
          "rule_or_exception": "whitespace_only"
        },
        {
          "case_key": "subject_23",
          "rule_or_exception": "whitespace_only"
        }
      ],
      "semantic_status": "candidate",
      "human_review_status": "pending"
    }
  }
]
```

原priority20存在`kind=content_repair`而消费端读取`overlay_kind`的格式差异；root已另存canonical overlay，不修改原文件。

新增overlay SHA-256：`2e99c4eaa3041507882c77305d6a6b8b527c19c80fcdbb7d4a17de1e4bcca0e1`。

首次F003693检查因新认定引文尚未绑定自己的behavior coverage而阻断，已将对应原penalty覆盖项改为behavior并缩短认定引文至具体事实句，随后冻结guard通过。最终9/9通过；requires_review信号仍保留，不等于人工批准。
