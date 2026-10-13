"""Build source-only E03 candidate cards and their exact-match audit.

Inputs are limited to the two frozen E02 source/unit packages. This helper does
not inspect queries, retrieval outputs, scores, PDFs, reserved sources or APIs.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT / "outputs" / "FinRisk_E02小批量实验_20261013"
OUTPUT_DIR = ROOT / "outputs" / "FinRisk_E01-E04五小时实验_20261013"
INPUT_PATHS = [INPUT_DIR / "prefix_inputs_p1.jsonl", INPUT_DIR / "prefix_inputs_p2.jsonl"]


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


rows = []
input_fingerprints = {}
for path in INPUT_PATHS:
    raw = path.read_bytes()
    input_fingerprints[path.name] = sha256_bytes(raw)
    rows.extend(json.loads(line) for line in raw.decode("utf-8-sig").splitlines() if line.strip())

assert len(rows) == 24
assert len({row["file_id"] for row in rows}) == 24
by_file = {row["file_id"]: row for row in rows}
for row in rows:
    assert sha256_bytes(row["full_source_text"].encode("utf-8")) == row["source_sha256"]
    assert row["unit"]["file_id"] == row["file_id"]
    assert row["unit"]["source_sha256"] == row["source_sha256"]
    assert row["unit"]["source_spans"]
    for span in row["unit"]["source_spans"]:
        assert row["full_source_text"][span["start"]:span["end"]] == row["unit"]["source_text"]


def literal_support(file_id, quote, role):
    row = by_file[file_id]
    source = row["full_source_text"]
    start = source.find(quote)
    assert start >= 0, (file_id, "quote missing")
    assert source.count(quote) == 1, (file_id, "quote has multiple positions")
    end = start + len(quote)
    assert source[start:end] == quote
    # A true unit reference must overlap the continuous quoted source region.
    assert any(start < s["end"] and end > s["start"] for s in row["unit"]["source_spans"])
    return {
        "file_id": file_id,
        "unit_id": row["unit"]["unit_id"],
        "source_sha256": row["source_sha256"],
        "quote": quote,
        "span": {"start": start, "end": end},
        "role": role,
    }


def range_support(file_id, start_literal, end_literal, role):
    source = by_file[file_id]["full_source_text"]
    assert source.count(start_literal) == 1, (file_id, "ambiguous start")
    start = source.index(start_literal)
    end = source.index(end_literal, start) + len(end_literal)
    return literal_support(file_id, source[start:end], role)


def card(card_id, title, mechanism, conditions, limitations, supports, retrieval_text):
    assert len({s["file_id"] for s in supports}) >= 2
    return {
        "card_id": card_id,
        "title": title,
        "mechanism": mechanism,
        "conditions": conditions,
        "boundary_notes": "未取得反例，待验证。这里只记录本样本的候选机制和核查方向，不据此对其他业务作监管结论。",
        "limitations": limitations,
        "supports": supports,
        "retrieval_text": retrieval_text,
        "status": "candidate_model",
        "human_approved": False,
    }


cards = [
    card(
        "E03-MC01",
        "保障责任、理赔服务及条款信息的宣传偏差",
        "样本中的销售话术或宣传材料可见夸大保险责任、理赔服务，或宣传内容与保险条款不一致、未告知附加险保费的事实。候选核查方向是逐项对比销售原话、宣传材料与对应条款及费用信息，定位承诺或告知内容的偏差。",
        "限于来源明确记载的销售或宣传活动：电话销售中的夸大服务和扩大责任、保险公司向代理机构提供的夸大责任材料、销售保险合同时宣传与条款不一致或未告知附加险保费。需要找到对应产品、销售表达与合同信息，不能仅靠夸大或销售等词作事实归因。",
        "三个支持来源只给出各自案情，未提供完整条款或全部销售资料，不能推断消费者实际理解、损失或一般因果关系。F008940是管理人员处罚文书所述的机构销售事实，不能把原话直接归为该个人亲自销售；F009587支持段补齐了原单元段首截断，回源时需核查完整连续段。",
        [
            literal_support(
                "F000699", by_file["F000699"]["unit"]["source_text"],
                "具体销售事实：电话销售中夸大理赔服务、擅自扩大保险责任",
            ),
            range_support(
                "F009587", "经查,平安产险菏泽中心支公司向其代理机构齐鲁保代菏泽分公司",
                "上述三种保险产品的宣传资料中,存在多项夸大保险责任等内容。",
                "具体材料事实：机构向代理机构提供的宣传资料夸大保险责任；本单元在连续段尾部",
            ),
            range_support(
                "F008940", "在销售P0600*号保险合同时,销售人员存在宣传内容",
                "未向投保人告知附加险保险费等内容;",
                "具体销售事实：宣传内容与条款不一致、未告知附加险保费；机构事实见于管理人员文书",
            ),
        ],
        "候选核查机制：保险销售宣传与条款信息偏离。电话销售夸大理赔手续、时效等服务，擅自扩大保险责任；向代理机构提供的保险产品宣传资料夸大保障责任；宣传内容与保险条款不一致，未向投保人告知附加险保险费。核对销售录音、宣传材料、对应条款和费用信息。",
    ),
    card(
        "E03-MC02",
        "合同外利益的承诺或给予",
        "样本出现承诺或给予保险合同约定以外利益的事实：一案书面承诺五年期分红险一年后给付本金，一案群内激励方案以保费金额对应赠送冰柜，另一简表仅记载给予投保人合同外利益。候选核查方向是确认利益内容、对象、合同依据及其与投保或缴费的关系。",
        "仅覆盖来源已明确记载合同外利益的承诺或给予。F003464与F009488有具体表达及销售关联，F006220只有案由层面的记载，不能为该简表补上礼品种类、金额、承诺方式或销售流程。",
        "各案产品、利益形态和事实详略不同，不能把五年期分红险提前本金承诺、保费门槛赠物及未展开的合同外利益视为同一操作流程。未取得合同完整文本；卡片不判断其他礼品或客户活动的一般合规性。F003464连续支持段包含原单元标题后的具体事实，不可将标题单独当作完整机制证据。",
        [
            range_support(
                "F003464", "一、承诺向客户给予合同规定以外的利益。",
                "涉及保单8件,保费30多万元。",
                "具体利益承诺：书面承诺五年期分红险一年后给付本金",
            ),
            literal_support(
                "F009488", by_file["F009488"]["unit"]["source_text"],
                "具体利益承诺：微信群激励方案按保费金额赠送客户冰柜",
            ),
            literal_support(
                "F006220", "给予投保人合同外利益;",
                "案由层面的补充支持：仅记载合同外利益，未展开具体给予方式",
            ),
        ],
        "候选核查机制：保险合同约定以外的利益承诺或给予。五年期分红险被书面承诺一年后给付本金；微信群激励方案将一万保费与赠送客户冰柜相联系；另有给予投保人合同外利益的案由。核查利益内容、对象、合同依据、投保和缴费关联。",
    ),
    card(
        "E03-MC03",
        "人身保险新型产品利益演示与课件宣传偏差",
        "两个来源共同记载相关课件有误导内容，并记载宣传资料或保单利益演示未按高、中、低三档演示未来利益给付。其中一案的产品说明会课件使用本金、分红金额表述。候选核查方向是核对来源所述产品类别、课件利益表达及利益演示范围。",
        "范围限于来源所述人身保险新型产品培训或产品说明会及宣传资料；F001128具体产品为合众聚富定投两全保险（分红型）。两案的三档演示问题只描述本案事实，不能扩展成全部保险产品或当前制度的统一要求。",
        "没有完整培训课件、展业册或利益测算表，不能恢复每档数值、计算过程或客户实际理解。F001978只说课件存在误导内容，未列出具体误导话术；不能把F001128的本金、分红数字或其他表达移植到F001978。",
        [
            literal_support(
                "F001978", by_file["F001978"]["unit"]["source_text"],
                "具体演示缺失事实：新型产品培训课件误导、宣传资料未按三档演示未来利益",
            ),
            literal_support(
                "F001128", by_file["F001128"]["unit"]["source_text"],
                "具体表达及演示缺失事实：产品说明会课件的本金、分红数字和未按三档演示",
            ),
        ],
        "候选核查机制：人身保险新型产品未来利益给付演示与宣传课件偏差。培训课件存在误导内容，宣传资料未按高、中、低三档演示；分红型产品说明会课件使用本金和分红金额，保单利益演示也未按三档展示。核查对应产品类别、课件表达、利益给付演示范围。",
    ),
    card(
        "E03-MC04",
        "虚挂中介业务后经手续费返还或转付套费",
        "两案均记载并非相应代理公司代理的保险业务被虚挂，向代理公司支付手续费，代理公司扣除一定费用后以现金或转账交还保险机构业务员，再转付其他代理人或代理机构，文书记载由此造成财务数据不真实。候选核查方向是核对真实代理关系、业务挂账及手续费最终去向，逐笔重建支付、扣费、返还或转付链条。",
        "需要同时有来源明确的非真实代理业务、虚挂及手续费扣费后返还或转付线索。各案的业务挂账主体必须按原文核查，不能把代理协议、手续费支付或返款中的单个现象直接归为该机制。",
        "两案均为历史文书，只有概括和汇总金额，缺逐笔流水、代理协议或发票。F003638原文写虚挂在本机构名下，该指代未在本卡中改成代理机构；卡片只抽取共同资金路径，不确定具体挂账方向。来源中的配合检查、立功和处罚裁量不属于机制适用条件。",
        [
            range_support(
                "F003497", "你公司把并非是纵横代理公司代理的保险业务虚挂在该公司名下",
                "导致财务业务数据不真实的行为,",
                "完整业务与资金路径：非代理业务虚挂、扣开票费、返还业务员并转付，及数据失实记载",
            ),
            range_support(
                "F003638", "经查,2007年,你分公司下属机构通过广州市鸿义保险代理有限公司",
                "你分公司下属机构上述做法造成财务数据不真实的行为,",
                "完整业务与资金路径：非代理业务虚挂、扣费、返还并转付，及数据失实记载；保留本机构指代",
            ),
        ],
        "候选核查机制：虚挂并非真实代理的保险业务套取手续费。保险机构向代理公司支付手续费，代理公司扣除开票费或一定费用后，以现金或转账返还业务员，再转支付其他代理人或机构；来源记载财务业务数据不真实。核对真实代理关系、业务挂账主体、手续费支付与最终收款人。",
    ),
]


audit = []
required_fields = {
    "card_id", "title", "mechanism", "conditions", "boundary_notes", "limitations",
    "supports", "retrieval_text", "status", "human_approved",
}
for item in cards:
    assert set(item) == required_fields
    assert item["status"] == "candidate_model" and item["human_approved"] is False
    assert "未取得反例，待验证" in item["boundary_notes"]
    for s in item["supports"]:
        row = by_file[s["file_id"]]
        start, end = s["span"]["start"], s["span"]["end"]
        match = row["full_source_text"][start:end] == s["quote"]
        unit_match = row["unit"]["unit_id"] == s["unit_id"]
        sha_match = sha256_bytes(row["full_source_text"].encode("utf-8")) == s["source_sha256"]
        contained = any(start >= p["start"] and end <= p["end"] for p in row["unit"]["source_spans"])
        overlap = any(start < p["end"] and end > p["start"] for p in row["unit"]["source_spans"])
        assert match and unit_match and sha_match and overlap
        audit.append({
            "card_id": item["card_id"], "file_id": s["file_id"], "chars": len(s["quote"]),
            "start": start, "end": end, "exact_match": match, "sha_match": sha_match,
            "unit_id_match": unit_match, "unit_overlap": overlap, "unit_contained": contained,
        })

assert len(cards) == 4
assert len(audit) == 10
assert len({s["file_id"] for c in cards for s in c["supports"]}) == 10
assert len({s["unit_id"] for c in cards for s in c["supports"]}) == 10

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
cards_path = OUTPUT_DIR / "mechanism_cards.jsonl"
cards_path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cards), encoding="utf-8")
# Check the saved artifact rather than only the in-memory objects.
saved_cards = [json.loads(line) for line in cards_path.read_text(encoding="utf-8").splitlines()]
assert saved_cards == cards
for path in INPUT_PATHS:
    assert sha256_bytes(path.read_bytes()) == input_fingerprints[path.name]

total_chars = sum(len(r["full_source_text"]) for r in rows)
unit_chars = sum(len(r["unit"]["source_text"]) for r in rows)
quote_chars = sum(a["chars"] for a in audit)
source_read_notes = {
    "F006493": "互联网销售不实信息、回溯管理及不正当诱导；不补具体话术或流程。",
    "F003464": "提前本金书面承诺、期限/收益误导及无代理合同支付；采用合同外利益具体段。",
    "F008940": "宣传与条款不一致、附加险费用未告知、赠礼；只采用条款/费用段。",
    "F008944": "与F008940同中心同保单事实的另一管理人员文书；不重复计入支持。",
    "F009488": "无执业登记个人与群内保费门槛赠物；采用合同外利益具体段。",
    "F009491": "与F009488同案主要负责人文书；不重复计入支持。",
    "F009587": "代理机构宣传材料夸大责任及虚挂中介手续费；仅采用与选定unit相交的宣传段。",
    "F000699": "电话销售虚假/夸大宣传及系统不能单独承保交强险；采用宣传完整unit。",
    "F004155": "多主体表格、合同外利益原话重复两位置；不纳入卡片支持。",
    "F001987": "保险/储蓄混淆与贷款说法不实；与F001988同案，选定unit只是证据概述。",
    "F001345": "倒签单影响保费/准备金、危险单位未合并；本样本不足同机制跨案支持。",
    "F004090": "多主体表格；选定unit为医护人员销售健康险，不将他行虚假资料混入。",
    "F006220": "农险多项案由；只取合同外利益短句作案由级补充。",
    "F001943": "误导课件/代抄风险提示、账外银行激励、团险证明；不移植他案具体演示条件。",
    "F001988": "保险/储蓄混淆与贷款宣传对照条款；与F001987同案，选定unit仅证据概述。",
    "F000742": "电销管理问题、万能型附加险、电销录音造假；选定unit截断，未凑跨案机制。",
    "F001978": "代抄提示、新型产品培训课件误导与未来利益未三档演示；采用后者完整unit。",
    "F002958": "保单未到期却以超期限拒赔且未查勘；未迁移具体条件到一般拒赔简表。",
    "F008852": "拒不履行赔偿/给付义务案由，无展开事实；不足支撑未到期拒赔共同机制。",
    "F003497": "非代理业务虚挂、扣开票费、返还/转付手续费；采用连续完整资金路径。",
    "F002890": "投资/高管、虚假资金和农险理赔退费资料、赔款挪作保费等；未混并为套中介手续费。",
    "F000269": "无本机构执业证销售、培训与撤销报告案由；无进一步操作细节，不扩写条件。",
    "F003638": "非代理业务虚挂、扣费后返还/转付；原文本机构指代保留，未擅改挂账方向。",
    "F001128": "分红型课件本金/分红数字、未三档演示及展业册表述；采用与选定unit一致段。",
}

notes = [
    "# E03轻量机制卡作者说明",
    "",
    "生成范围：只读原E02 prefix_inputs_p1.jsonl与prefix_inputs_p2.jsonl中的24份全文和24个选定单元，未看查询、候选结果、评分或旧模型效果；未读取360预留正文、教材PDF、.env，未调用项目API，未修改旧输入。卡片先写成candidate_model且human_approved=false，根审核通过前不进入候选路。",
    "",
    f"实际逐篇阅读24份全文，共{total_chars}个Unicode字符（含换行）；所列24个source_text合计{unit_chars}字符。24/24全文UTF-8 SHA256与source_sha256一致，24/24源单元所有已列source_spans逐字匹配。F004155有两处同文位置，保留这一观察且不采用它作支持。",
    "",
    f"交付4张候选卡，10份不同file、10个真实unit_id、10条支持，支持原话合计{quote_chars}字符；全部支持source_sha256、unit_id、连续quote与span逐字核验通过。区间采用Python字符偏移，起点含、终点不含（[start,end)），以工作包full_source_text为基准，不以PDF字节偏移为基准。",
    "",
    "这里只做源中可支持的候选机制和核查提示，retrieval_text是模型概括，不是监管原话。最终第三路只能由审核通过的supports.unit_id召回既有案例，再对原单元重排/返回；不能把card.mechanism或retrieval_text当证据、监管答案或人类批准。",
    "",
    "## 选卡与不足",
    "",
    "1. 宣传与保障/条款信息偏差：F000699、F009587、F008940各有具体销售或材料事实，个人责任文书中的机构事实保持角色区分。",
    "2. 合同外利益：F003464、F009488有具体利益表达；F006220仅作案由级补充，其未展开部分不补造细节。",
    "3. 新型产品利益演示：F001978、F001128有共同未三档演示的事实，明确限制产品和资料范围，不生成现行制度结论。",
    "4. 虚挂中介业务套费：F003497、F003638均有业务不真实、支付/扣费/返还或转付链条；F003638原文虚挂在本机构名下的指代未改写。",
    "",
    "没有凑第五张拒赔卡：F002958有保单未到期、以超期限拒赔、未查勘的具体事实，F008852只有一般拒赔/给付义务案由，不能用后者确认前者的具体机制条件。倒签单/准备金、危险单位合并、万能附加险销售、承保录音造假等也没有本次24源内与选定单元足够贴合的跨文件机制支持，后置。",
    "",
    "未取得真实反例，四张boundary_notes均明确写未取得反例，待验证。条件收窄或不作判断不冒称真实反例。没有依赖查询关键词形成卡片。",
    "",
    "## 源区间与召回限制",
    "",
    "6条支持quote包含于选定单元，4条支持从全文补齐与真实unit相交的连续事实：MC01/F009587段首截断、MC02/F003464只有标题、MC04/F003497句尾截断、MC04/F003638段首截断。支持延展没有生成新单元ID或变更原单元。后续返回原单元时，若只有标题或断句，必须靠可回源的真实context/全文核查；卡片延展quote不能伪装成原返回文本，也不能静默当作原单元已完整覆盖机制。",
    "",
    "同案重复控制：F008940与F008944为同中心同保单事实的不同管理人员文书；F009488与F009491是机构及负责人；F001987与F001988是机构及主管。前两组只各取一文件，最后一组未入卡支持。本卡10份支持来源不使用上述同案文件对作为跨案重复验证。不同file数量不是统计独立性的证明。",
    "",
    "## 全部支持逐字匹配结果",
    "",
    "| 卡ID | 文件 | 连续区间 | quote字符 | quote逐字 | SHA | unit_id | 与unit相交 | quote包含于unit |",
    "|---|---|---|---:|---|---|---|---|---|",
]
for a in audit:
    notes.append(
        f"| {a['card_id']} | {a['file_id']} | [{a['start']},{a['end']}) | {a['chars']} | PASS | PASS | PASS | PASS | {'是' if a['unit_contained'] else '否，全文连续延展'} |"
    )
notes.extend([
    "",
    "逐条quote已直接从对应full_source_text连续提取，未去换行、未标准化标点、未拼接非相邻片段；源SHA与真实unit_id由对应工作包行取出。保存JSONL后重新读取并与内存对象相等核验，10/10全部匹配通过。",
    "",
    "## 24篇实际阅读登记",
    "",
    "| 文件 | 全文字符 | SHA核验 | 阅读要点与处理 |",
    "|---|---:|---|---|",
])
for row in rows:
    notes.append(f"| {row['file_id']} | {len(row['full_source_text'])} | PASS | {source_read_notes[row['file_id']]} |")
notes.extend(["", "## 输入指纹（生成前后相同）", ""])
for name, fingerprint in input_fingerprints.items():
    notes.append(f"- {name}: `{fingerprint}`")
notes.extend([
    "",
    f"mechanism_cards.jsonl SHA256: `{sha256_bytes(cards_path.read_bytes())}`",
    "",
    "本文件记录模型作者实际阅读及机械核验，不能替代根审核，也不声明真人批准。",
])
(OUTPUT_DIR / "mechanism_notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")

print(json.dumps({
    "cards": len(cards), "support_files": len({s["file_id"] for c in cards for s in c["supports"]}),
    "supports": len(audit), "full_source_count_read": len(rows), "full_source_chars_read": total_chars,
    "source_unit_chars": unit_chars, "support_quote_chars": quote_chars,
    "all_quote_sha_unit_matches": all(a["exact_match"] and a["sha_match"] and a["unit_id_match"] and a["unit_overlap"] for a in audit),
    "unit_contained_supports": sum(a["unit_contained"] for a in audit),
    "extended_supports": sum(not a["unit_contained"] for a in audit),
    "audit": audit, "cards_sha256": sha256_bytes(cards_path.read_bytes()),
}, ensure_ascii=False, indent=2))
