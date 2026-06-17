"""script-control-center 脚本中加载 CE 基址配置的示例。"""

from ce_base_extractor.integrations.scc import chain_to_reader_args, load_bases

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python scc_loader.py mygame_scc.json")
        raise SystemExit(1)
    cfg = load_bases(sys.argv[1])
    print(f"游戏配置: {cfg.get('preset')}  链数: {len(cfg['chains'])}")
    for c in cfg["chains"]:
        print(chain_to_reader_args(c))
