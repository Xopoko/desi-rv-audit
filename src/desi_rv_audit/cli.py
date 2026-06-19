from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import load_and_run
from .plots import write_plots
from .report import build_report, write_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="desi-rv-audit",
        description="Audit multi-epoch radial-velocity measurements.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze CSV, Parquet, or FITS epoch tables")
    analyze.add_argument("inputs", nargs="+", help="One or more input files")
    analyze.add_argument("--output-dir", required=True)
    analyze.add_argument("--max-rows-per-file", type=int)
    analyze.add_argument("--min-sn-r", type=float, default=5.0)
    analyze.add_argument("--max-pairs-per-source", type=int, default=50)
    analyze.add_argument(
        "--lite-output",
        action="store_true",
        help="Skip full source_summary.csv and pairs.csv; write compact sidecars and screening outliers.",
    )
    analyze.add_argument(
        "--report-output",
        help="Write a Markdown report directly from in-memory analysis outputs.",
    )
    analyze.add_argument(
        "--backup-correction",
        help="Optional FITS/CSV/Parquet table with TARGETID and VRAD_OFFSET/VRAD_BIAS.",
    )
    analyze.add_argument(
        "--backup-correction-md5",
        default="f48a4b21b541e94d61f4372f4c555f12",
        help="Expected MD5 for the backup correction file. Use an empty string to skip.",
    )
    analyze.add_argument(
        "--strict-desi-main",
        action="store_true",
        help="Require DESI DR1 MAIN FITS extensions/columns and row alignment checks.",
    )
    analyze.add_argument(
        "--plots",
        action="store_true",
        help="Write diagnostic PNG plots to the output directory.",
    )
    analyze.add_argument(
        "--program-night-audit",
        action="store_true",
        help="Run five-fold source-grouped PROGRAM:NIGHT residual diagnostics.",
    )
    analyze.add_argument("--program-night-folds", type=int, default=5)
    analyze.add_argument("--program-night-min-pairs-per-label", type=int, default=200)
    analyze.add_argument("--program-night-max-abs-z", type=float, default=5.0)
    analyze.add_argument("--program-night-clip-sigma", type=float, default=3.5)
    analyze.add_argument("--program-night-clip-iterations", type=int, default=3)
    analyze.add_argument("--program-night-damp", type=float, default=0.2)
    analyze.add_argument("--program-night-min-delta-days", type=float, default=1.0)
    analyze.add_argument("--program-night-permutations", type=int, default=20)
    analyze.add_argument(
        "--no-program-night-permutation",
        action="store_true",
        help="Skip deterministic shuffled-night control for PROGRAM:NIGHT diagnostics.",
    )

    report = subparsers.add_parser("report", help="Build a Markdown report")
    report.add_argument("--source-summary", required=True)
    report.add_argument("--pairs", required=True)
    report.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "analyze":
        outputs = load_and_run(
            args.inputs,
            args.output_dir,
            max_rows_per_file=args.max_rows_per_file,
            min_sn_r=args.min_sn_r,
            max_pairs_per_source=args.max_pairs_per_source,
            write_heavy_outputs=not args.lite_output,
            backup_correction_path=args.backup_correction,
            backup_correction_md5=args.backup_correction_md5 or None,
            strict_desi_main=args.strict_desi_main,
            run_program_night=args.program_night_audit,
            program_night_folds=args.program_night_folds,
            program_night_min_pairs_per_label=args.program_night_min_pairs_per_label,
            program_night_max_abs_z=args.program_night_max_abs_z,
            program_night_clip_sigma=args.program_night_clip_sigma,
            program_night_clip_iterations=args.program_night_clip_iterations,
            program_night_damp=args.program_night_damp,
            program_night_min_delta_days=args.program_night_min_delta_days,
            program_night_run_permutation=not args.no_program_night_permutation,
            program_night_permutations=args.program_night_permutations,
        )
        if args.report_output:
            report_text = build_report(
                outputs.source_summary,
                outputs.pairs,
                epoch_quality_by_program=outputs.epoch_quality_by_program,
                calibration_overall=outputs.calibration_overall,
                calibration_formal_overall=outputs.calibration_formal_overall,
                calibration_by_program=outputs.calibration_by_program,
                calibration_formal_by_program=outputs.calibration_formal_by_program,
                calibration_interday_by_program=outputs.calibration_interday_by_program,
                calibration_formal_interday_by_program=(
                    outputs.calibration_formal_interday_by_program
                ),
                calibration_by_sn=outputs.calibration_by_sn,
                rejection_counts=outputs.rejection_counts,
                correction_summary=outputs.correction_summary,
                program_night_summary=outputs.program_night_summary,
                program_night_by_program=outputs.program_night_by_program,
                program_night_reproducibility=outputs.program_night_reproducibility,
                program_night_permutation_summary=outputs.program_night_permutation_summary,
            )
            report_path = Path(args.report_output)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_text, encoding="utf-8")
        if args.plots:
            write_plots(outputs, args.output_dir)
        candidates = int((outputs.source_summary["classification"] == "candidate_variable").sum())
        output_mode = "lite outputs" if args.lite_output else "full outputs"
        print(
            f"Analyzed {len(outputs.source_summary)} sources and {len(outputs.pairs)} epoch pairs; "
            f"screened {candidates} constant-RV outlier sources; wrote {output_mode}."
        )
    elif args.command == "report":
        write_report(args.source_summary, args.pairs, args.output)
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
