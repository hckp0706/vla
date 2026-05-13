import argparse
import sys
import json
from m6_semantic_tool.converter import SemanticConverter


def main():
    parser = argparse.ArgumentParser(description="M6 数据语义化转换工具")
    parser.add_argument("-i", "--input", required=True, help="M2 综合融合航迹 JSON 文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径（默认输出到控制台）")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    args = parser.parse_args()

    converter = SemanticConverter()
    report = converter.convert_from_file(args.input)

    if args.format == "json":
        output = json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=str)
    else:
        output = report.to_text()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"已输出到 {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
