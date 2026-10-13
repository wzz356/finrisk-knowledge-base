"""Source-bound session authoring for the two upper recursive summary stages."""
import argparse
from e07 import OUT, demo
from author_nodes import refs

PROMO = ["F001987","F001988","F008940","F008944","F009587","F000699","F001943"]
BENEFIT = ["F003464","F009488","F009491","F004155","F001128","F001978"]
OTHER = ["F004090","F000742","F002958","F001345","F003497","F003638","F002890"]


def main(mode):
    leaves = {leaf["file_id"]:leaf for leaf in demo.rows(OUT / "leaves.jsonl")}
    if mode == "level2":
        clusters = demo.read_json(OUT / "clusters_level2.json")["clusters"]
        manual = {
            0:("单一案由片段的合同赔付义务", [("当前叶片段仅列拒不履行合同赔付义务，具体原因、流程和主体未展开。",["F008852"])]),
            1:("多机制历史事实与条件导航", [
                ("来源分别有宣传与条款/费用、保障及理赔服务偏差、误导课件。",PROMO),
                ("合同外利益与新型未来利益演示为另外的历史事实。",BENEFIT),
                ("渠道、赔付、记录及手续费/赔款流向问题分别保存。",OTHER)])}
        target = OUT / "summaries_level2.jsonl"; level=2
    else:
        clusters = demo.read_json(OUT / "clusters_level3.json")["clusters"]
        manual = {0:("历史风险案例的多层原文导航", [
            ("多个历史来源分别涉及宣传与条款/费用/保障或服务偏差、合同外利益和未来利益演示。",PROMO+BENEFIT),
            ("另有渠道、记录、资金流向与赔付问题，具体机制和条件分别回叶原文。",OTHER),
            ("仅案由的赔付叶不补具体原因、流程和主体。",["F008852"])])}
        target=OUT / "summaries_level3.jsonl"; level=3
    result=[]
    for cluster in clusters:
        title, claims_spec=manual[cluster["cluster_id"]]
        wanted=set(cluster["descendant_unit_ids"])
        actual={leaves[fid]["unit_id"] for _,files in claims_spec for fid in files}
        if actual!=wanted:raise ValueError("Upper claim sources differ from actual clustered descendants")
        claims=[{"claim_id":f"L{level}:{cluster['cluster_id']}:{i}","text":text,"supports":refs(files,leaves)}
                for i,(text,files) in enumerate(claims_spec,1)]
        limitation="不同机构/个人责任、产品、条件与事件分别保留；同簇不等于同机制或同事件，历史要求不当当前通则。"
        result.append({"node_id":f"TREE:L{level}:{cluster['cluster_id']}","level":level,
            "child_node_ids":cluster["member_node_ids"],"descendant_unit_ids":cluster["descendant_unit_ids"],
            "text":title + "。" + "".join(c["text"] for c in claims) + limitation,
            "claims":claims,"limitations":limitation,"human_approved":False,"author":"current_session_model",
            "cluster_input_sha256":demo.sha_file(OUT / f"clusters_level{level}.json")})
    demo.write_new(target,result,True)
    if mode=="root":
        all_nodes=[]
        for n in (1,2,3):all_nodes+=demo.rows(OUT / f"summaries_level{n}.jsonl")
        demo.write_new(OUT / "tree_nodes.jsonl",all_nodes,True)


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["level2","root"]);main(p.parse_args().mode)
