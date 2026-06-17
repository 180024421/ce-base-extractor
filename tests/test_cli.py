from ce_base_extractor import __main__ as cli


def test_legacy_extract_help():
    parser = cli._build_legacy_parser()
    args = parser.parse_args(["scan.sqlite", "--format", "json"])
    assert args.input == "scan.sqlite"
    assert args.format == "json"


def test_subcommand_diff_parser():
    parser = cli.build_parser()
    args = parser.parse_args(["diff", "a.sqlite", "b.sqlite", "--ptrid", "1"])
    assert args.command == "diff"
    assert len(args.files) == 2
    assert args.ptrid == 1
