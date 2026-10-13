"""Validate and export explicit session-authored three-state information checklists."""
import hashlib
import importlib.util
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
OUT = ROOT / "outputs/FinRisk_E07_E06_E05探索_20261013"
spec = importlib.util.spec_from_file_location("e07_frozen_demo", ROOT / "work/finrisk_demo_v3_20261013/demo.py")
demo = importlib.util.module_from_spec(spec); spec.loader.exec_module(demo)


def validate_input_record(record, field_ids):
    rows = record["conditions"]
    if len({x["field_id"] for x in rows}) != len(rows) or {x["field_id"] for x in rows} != field_ids:
        raise ValueError("Missing/duplicate condition field")
    missing = []
    for row in rows:
        if row["state"] not in {"present", "absent", "unknown"}:
            raise ValueError("Condition state must be present/absent/unknown")
        quote = row["quote"]
        if not isinstance(quote, str) or quote and quote not in record["text"]:
            raise ValueError("Condition quote not in actual input")
        if row["state"] != "unknown" and not quote:
            raise ValueError("Non-unknown condition requires an explicit input quote")
        if row["state"] == "unknown":
            missing.append(row["field_id"])
    return missing


def followup_fields(record):
    by_id = {row["field_id"]: row for row in record["conditions"]}
    suppressed = set()
    if record["mechanism_id"] == "extra_benefit" and by_id["extra_benefit_claimed"]["state"] == "absent":
        suppressed.update({"purchase_link_stated", "delivery_known"})
    return [row["field_id"] for row in record["conditions"] if row["state"] == "unknown" and row["field_id"] not in suppressed]


def support(file_id, quote, sources):
    source = sources[file_id]
    spans = []; start = 0
    while True:
        start = source.find(quote, start)
        if start < 0: break
        spans.append({"start": start, "end": start + len(quote)}); start += 1
    if not spans:
        raise ValueError("Checklist support is not exact source quote")
    return {"file_id": file_id, "quote": quote, "spans": spans,
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest()}


PROFILE_SPECS = {
"coverage": ("给付宣传与条款条件", "F009587", "称“确诊即赔”。上述三种保险产品的宣传资料中,存在多项夸大保险责任等内容。", [
 ("terms_available","能提供具体产品合同、疾病定义、等待期、免责及给付条件吗？"),
 ("limits_disclosed","销售原话是否实际说明限制/免责条件？"),
 ("unconditional_payment_claimed","是否把某事件发生说成无条件/即时给付？"),
 ("promise_terms_match_known","宣传给付与实际条款是否一致，依据是什么？")]),
"extra_benefit": ("合同外利益", "F003464", "书面承诺约定五年期分红险业务一年后“给付本金”", [
 ("extra_benefit_claimed","是否有额外利益承诺，具体给什么、给谁？"),
 ("benefit_in_contract","该利益是合同约定的给付还是另行承诺？"),
 ("purchase_link_stated","利益是否和投保/缴费关联？"),
 ("delivery_known","承诺是否已经兑现，能提供记录吗？")]),
"agency_fees": ("代理业务归属与手续费流向", "F003497", "你公司把并非是纵横代理公司代理的保险业务虚挂在该公司名下", [
 ("actual_agent_participation","收款方实际参与了哪些代理服务，证据是什么？"),
 ("record_actual_match","逐单挂账归属与实际销售服务一致吗？"),
 ("authorization_stated","是否有授权及合同，覆盖哪些业务和时点？"),
 ("return_flow_stated","手续费最终给谁，有没有扣费后回流/转付？")]),
"returns": ("利益演示、保证性质与条件", "F001128", "保单利益演示部分未按照高、中、低三档演示新型产品未\n来的利益给付。", [
 ("product_type_stated","具体是什么产品类型，数字对应哪些期限？"),
 ("guarantee_basis_known","哪些数字由合同保证，哪些是非保证演示？"),
 ("full_material_available","能提供完整演示/宣传及实际条款吗？"),
 ("uncertainty_disclosed","是否说明假设、未来不确定性和适用条件？"),
 ("fees_disclosed","是否提示对应费用，金额或计算方式是什么？")]),
"license": ("本机构证书与销售时点", "F006527", "委托未持有本机构发放的执业证书的人\n员从事保险销售行为", [
 ("issuer_certificate_stated","是否已持本机构发放执业证，证书/登记时点是什么？"),
 ("sales_activity_stated","是已经开展销售，还是仅有安排/计划？"),
 ("registration_stated","是否完成本机构执业登记，人员类型及授权是什么？")]),
"agri_claim": ("真实损失与赔款用途", "F002890", "存在虚增赔款及截留赔款资金的问题。", [
 ("real_loss_stated","实际灾害/损失是否存在，有哪些证明？"),
 ("survey_verified_stated","是否实际查勘并核实损失/标的？"),
 ("payout_diversion_stated","赔款最终到谁的账户，是否被抵费/回流/截留？")]),
"service": ("理赔服务宣传与实际服务", "F000699", "对理赔手\n续、时效等服务夸大宣传", [
 ("full_sales_material_available","能提供完整销售录音/宣传原话吗？"),
 ("concrete_commitment_known","具体承诺了哪些便利条件、办理时间或到账时长？"),
 ("actual_process_known","实际流程、条件、服务时效及履行记录是什么？"),
 ("commitment_matches_service_known","对照实际服务，哪些承诺符合、超出或无法核实？")])}

# Explicit input reading, not a keyword-based condition extractor. P/A/U refer to text claims only.
INPUT_SPECS = {
"D001": ("coverage", [("U",""),("A","不用讲免责事项"),("P","医院出具确诊书后当天就能拿到保险金"),("U","")]),
"D002": ("coverage", [("U",""),("P","合同约定的疾病定义、等待期和免责事项"),("A","确诊后仍要核对合同约定"),("U","")]),
"D003": ("extra_benefit", [("P","部分保费作为现金补贴返给客户"),("A","这笔补贴没有写入保险合同"),("P","投保后"),("U","")]),
"D004": ("extra_benefit", [("A","没有另外承诺返现、礼品或其他利益"),("P","均写在本次保险合同内"),("U",""),("U","")]),
"D005": ("agency_fees", [("A","没有代理人参与"),("A","财务仍把业务挂到代理人名下支付手续费"),("U",""),("P","再让代理人转回")]),
"D006": ("agency_fees", [("P","代理人实际参与客户沟通和投保服务"),("P","业务归属和服务记录与本人一致"),("U","合同约定的手续费"),("U","未要求资金转回")]),
"D007": ("returns", [("P","万能险"),("U",""),("U",""),("A","不用考虑结算变化"),("A","不用考虑结算变化和费用扣除")]),
"D008": ("returns", [("P","万能险"),("P","分别列明合同保证利率和历史结算利率"),("U",""),("P","历史结算不代表未来，未来可能变化"),("P","提示相关费用和风险")]),
"D009": ("license", [("A","尚未取得本机构发放执业证书"),("P","公司打算先开展销售再补办证书"),("U","")]),
"D010": ("license", [("P","持有本机构发放的执业证书"),("U",""),("P","已完成本机构登记")]),
"D011": ("agri_claim", [("A","没有实际灾害损失"),("U","编造受灾面积"),("P","用来返还此前由村组垫付的保费")]),
"D012": ("agri_claim", [("P","发生合同约定的灾害损失"),("P","查勘核实后按实际损失"),("A","没有扣留赔款抵缴保费")]),
"D013": ("service", [("A","没有保存完整录音"),("U","未核清实际服务流程和具体承诺时长"),("U","未核清实际服务流程和具体承诺时长"),("U","")]),
"D014": ("returns", [("U","产品类型"),("U","数字是否保证"),("U","一张保险产品利益演示截图"),("U","销售员解释均未提供"),("U","")]),
"D015": ("agency_fees", [("U","尚不清楚个人是否实际参与销售"),("U",""),("U","是否有授权"),("U","资金是否转回公司")]),
"D016": ("returns", [("U",""),("U","金额是否保证"),("U","没有合同、给付条件、金额是否保证和完整视频"),("U",""),("U","")])}

BRANCHES = [
 ("D013","risk", "取得完整录音：销售承诺无论材料是否齐全，报案当天保险金一定到账；实际公示和办理记录为资料齐全后通常5个工作日。", "risk_detected", ["销售误导","虚假宣传"], "具体承诺与实际条件及时效不一致；此前便利/快速形容词不足，现在有可核对差异。"),
 ("D013","boundary", "取得完整宣传：快速指线上上传并在资料齐全后5个工作日内办理，限制条件一并说明；核对公示流程和履行记录均符合该时间，没有当天或无条件到账承诺。", "no_obvious_risk", [], "补充后的具体宣传与服务条件/时效一致，本段未见明确夸大，不证明整项业务合规。"),
 ("D014","risk", "完整材料表明产品为分红型，销售员把图中未来分红数字明确承诺为每年固定保证收益；实际合同注明分红不保证。", "risk_detected", ["销售误导","保证收益"], "非保证利益被作为固定保证，差异足以提示风险；不凭数字数量定性。"),
 ("D014","boundary", "完整材料区分不同期限的合同保证给付和非保证演示，明确假设、费用和不确定性；销售录音与这些说明一致，未将演示收益说成未来保证。", "no_obvious_risk", [], "补充信息排除了本次关注的保证混淆；具体格式适用规则需另核。"),
 ("D015","risk", "核实个人没有参与这些保单服务，实际为公司直销；账面挂个人代理并支付手续费，个人扣费后转回公司用于其他开支。", "risk_detected", ["虚列费用套取资金"], "实际业务与挂账错配、手续费回流同时出现；金额和人员责任仍待核。"),
 ("D015","boundary", "个人有覆盖该业务的授权和代理合同，实际参与客户沟通投保服务，逐单记录与收款人一致；手续费按合同支付，没有回流或虚假列支。", "no_obvious_risk", [], "真实服务、归属与合同付款一致，个人收款本身不构成套费。"),
 ("D016","risk", "取得合同和完整视频：合同不存在宣传所说的满期固定现金给付，销售仍宣称该金额保证到账，且未说明须满足的给付条件。", "risk_detected", ["销售误导","虚假宣传","隐瞒重要信息"], "不存在的利益与遗漏给付条件明确，但尚不确定实际成交或损失。"),
 ("D016","boundary", "合同明确约定满期在被保险人满足约定条件时给付所列保证金额，视频完整说明这些条件，分红另标非保证；宣传与合同一致。", "no_obvious_risk", [], "合同内有条件给付与宣传一致，不把满期领取表述本身判违规。")]


def main(destination=OUT):
    sources = demo.source_map()
    queries = {q["query_id"]: q for q in demo.rows(OUT / "queries.jsonl")}
    profiles = []
    for pid, (name, fid, quote, questions) in PROFILE_SPECS.items():
        profiles.append({"mechanism_id": pid, "title": name, "support": support(fid, quote, sources),
            "questions": [{"field_id": field, "question": question, "priority": index + 1} for index, (field, question) in enumerate(questions)],
            "limitations": "核查提示及顺序是工程假设，不是统计重要性/因果或新监管规则；历史产品、场景及责任适用须核对。",
            "human_approved": False})
    by_id = {p["mechanism_id"]: p for p in profiles}
    records = []
    codes = {"P": "present", "A": "absent", "U": "unknown"}
    for qid, (pid, values) in INPUT_SPECS.items():
        profile = by_id[pid]; query = queries[qid]
        if len(values) != len(profile["questions"]): raise ValueError("Condition count mismatch")
        record = {"query_id": qid, "text": query["text"], "mechanism_id": pid,
            "condition_interpretation": "状态只表示输入如何记载，不等于事实已经外部核实；present包含明确计划，未知不补成否。",
            "conditions": [{"field_id": question["field_id"], "state": codes[code], "quote": quote}
                           for question, (code, quote) in zip(profile["questions"], values)], "human_approved": False}
        missing = validate_input_record(record, {q["field_id"] for q in profile["questions"]})
        ask_fields = followup_fields(record)
        record["followup_questions"] = [q for q in profile["questions"] if q["field_id"] in ask_fields]
        record["unknown_fields_not_asked"] = [field for field in missing if field not in ask_fields]
        record["source_support"] = profile["support"]
        record["source_support_role"] = "mechanism_checklist_origin_not_this_query_retrieved_evidence"
        record["notes"] = "unknown才触发待补问题；explicit absent保留否定，不自动当已取得证明。"
        if qid == "D006": record["notes"] += "代理合同不等于已提供完整授权文件；未要求回流不等于实际未回流，均保留未知。"
        if qid == "D009": record["notes"] += "仅计划开展销售，不把计划升级成已销售事实。"
        records.append(record)
    branches = [{"branch_id": qid + "-" + name, "parent_query_id": qid, "provided_information": text,
        "decision": decision, "candidate_labels": labels, "reason": reason, "origin": "constructed_information_branch_current_session",
        "not_real_customer_material": True, "human_approved": False, "new_retrieval_performed": False}
        for qid, name, text, decision, labels, reason in BRANCHES]
    demo.write_new(destination / "e07_profiles.jsonl", profiles, True)
    demo.write_new(destination / "e07_input_checks.jsonl", records, True)
    demo.write_new(destination / "e07_information_branches.jsonl", branches, True)
    counts = {state: sum(c["state"] == state for record in records for c in record["conditions"]) for state in codes.values()}
    demo.write_new(destination / "e07_execution.json", {"status": "complete_exploratory_condition_replay", "profiles": 7,
        "inputs": 16, "state_counts": counts, "followup_questions": sum(len(r["followup_questions"]) for r in records),
        "dependent_unknown_questions_suppressed": sum(len(r["unknown_fields_not_asked"]) for r in records), "constructed_branches": 8,
        "branch_model_decisions": {"risk_detected": 4, "no_obvious_risk": 4}, "automatic_dialogue_deployed": False,
        "new_retrieval_performed_for_branches": False, "independent_gold": False,
        "author_is_judge": True, "human_approved": False,
        "conclusion": "Structured unknowns and source-backed questions are usable; branch outcomes demonstrate condition sensitivity, not an accuracy improvement over V3 which already lists the main gaps."})
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__": main()
