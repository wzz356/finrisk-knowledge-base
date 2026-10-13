"""Serialize explicit source-grounded session summaries after actual clustering."""
import json
from e07 import OUT, demo

L1 = {
0: ("条款、渠道、记录与资金的混合簇", [
 ("保险被混同储蓄，贷款宣传与现金价值/利息条件不符。", ["F001987","F001988"]),
 ("另有委托医护售健康险、电销包含万能附加险的历史事实。", ["F004090","F000742"]),
 ("新型产品课件误导且未来利益未按三档演示。", ["F001978"]),
 ("延迟签单使收入和准备金不真实；农险资料造假及赔款抵费分别记载。", ["F001345","F002890"]),
 ("非真实代理业务被虚挂，手续费扣费后返还或转付。", ["F003638"])]),
1: ("宣传告知、赔付和套费的混合簇", [
 ("管理人员文书记载机构宣传不符条款、附加险费未告知和赠礼。", ["F008940","F008944"]),
 ("机构材料夸大保障；电销夸大理赔手续时效；课件误导及代抄风险提示另见。", ["F009587","F000699","F001943"]),
 ("表格两行分别列合同外利益，其中人员行另列销售误导。", ["F004155"]),
 ("机构在保单未到期时以超期拒查勘赔付，个人负直接责任。", ["F002958"]),
 ("另有虚挂代理并经手续费返还转付套费。", ["F003497"])]),
2: ("合同外利益与分红利益演示", [
 ("五年期分红险被书面承诺一年后给付本金。", ["F003464"]),
 ("缴费赠冰柜方案与负责人的直接领导责任分开记载。", ["F009488","F009491"]),
 ("分红型产说会课件使用本金/分红数字，未来利益未按三档演示。", ["F001128"])]),
3: ("仅有案由的合同赔付义务片段", [
 ("当前叶片段仅记载拒不依法履行合同约定的赔偿或者给付保险金义务。", ["F008852"])])}

DIRECTORY = [
 ("DIR:promotions", "宣传与合同/费用告知", ["F008940","F008944","F009587","F000699","F001943","F001987","F001988"],
  "来源分别涉及保险与储蓄/贷款话术偏差、保障责任或理赔手续时效夸大、附加险费未告知、课件误导与代抄风险提示。"),
 ("DIR:extra", "合同外利益", ["F003464","F009488","F009491","F004155"],
  "来源分别记载提前本金承诺、缴费赠冰柜及合同外利益案由；表行和管理人员责任不混合。"),
 ("DIR:illustrations", "新型产品未来利益演示", ["F001978","F001128"],
  "来源记载培训/产说会课件误导与未来利益未按三档演示，限历史产品与场景，不外推全部当前产品。"),
 ("DIR:finance", "记录真实性与费用/赔款资金路径", ["F001345","F003497","F003638","F002890"],
  "延迟出单的收入准备金失真、虚挂代理手续费返还转付、农险资料造假及赔款抵费是不同机制，分别核查记录和流向。"),
 ("DIR:channel", "历史销售渠道与产品范围", ["F004090","F000742"],
  "分别有委托医护人员销售健康险、电销包含万能附加险的历史事实，不能据此归所有渠道同一违法。"),
 ("DIR:claims", "合同赔付与拒绝查勘", ["F002958","F008852"],
  "一来源记载未到期却以超期拒查勘赔付及个人责任；另一叶仅列拒履行合同赔付案由，具体原因未知。")]


def refs(files, leaves):
    return [{"file_id": fid, "node_id": leaves[fid]["node_id"], "unit_id": leaves[fid]["unit_id"],
             "source_sha256": leaves[fid]["source_sha256"], "segments": leaves[fid]["segments"]} for fid in files]


def make_level1():
    leaves = {leaf["file_id"]: leaf for leaf in demo.rows(OUT / "leaves.jsonl")}
    clusters = demo.read_json(OUT / "clusters_level1.json")["clusters"]
    summaries = []
    for cluster in clusters:
        title, manual = L1[cluster["cluster_id"]]
        children = cluster["member_node_ids"]
        files = {member["node_id"].split(":", 1)[1] for member in cluster["members"]}
        if {fid for _, fids in manual for fid in fids} != files: raise ValueError("Summary claims must cover actual cluster leaves")
        claims = [{"claim_id":f"L1:{cluster['cluster_id']}:{i}", "text":text, "supports":refs(fids, leaves)}
                  for i, (text, fids) in enumerate(manual, 1)]
        limits = "不同案例与表行不合并主体/事件；管理责任不等于亲自实施；未展开条件保持未知，历史要求不当当前通则。"
        if cluster["cluster_id"] == 3: limits = "具体拒赔原因、流程、主体和产品在此叶片段未展开，不能补成通用规则。"
        summaries.append({"node_id":f"TREE:L1:{cluster['cluster_id']}", "level":1, "child_node_ids":children,
            "descendant_unit_ids":cluster["descendant_unit_ids"], "text":title + "。" + "".join(c["text"] for c in claims) + limits,
            "claims":claims, "limitations":limits, "human_approved":False,
            "cluster_input_sha256":demo.sha_file(OUT / "clusters_level1.json"), "author":"current_session_model"})
    directory=[]
    for node_id, title, files, text in DIRECTORY:
        directory.append({"node_id":node_id,"level":1,"text":title + "。" + text,
            "descendant_unit_ids":[leaves[fid]["unit_id"] for fid in files], "source_leaf_ids":[leaves[fid]["node_id"] for fid in files],
            "claims":[{"claim_id":node_id+":1","text":text,"supports":refs(files,leaves)}],
            "human_approved":False,"author":"current_session_model_from_source_mechanisms_not_clustering"})
    demo.write_new(OUT / "summaries_level1.jsonl",summaries,True)
    demo.write_new(OUT / "directory_nodes.jsonl",directory,True)


if __name__ == "__main__": make_level1()
