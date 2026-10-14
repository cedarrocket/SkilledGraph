"""Local inference is explicitly opt-in; no calls during test discovery."""
from pathlib import Path
import sys

from skilledgraph.cli import launch

if __name__=='__main__':
    workflow=Path(__file__).resolve().parents[1]/'lmstudio_briefing/workflow_cn.md'
    raise SystemExit(launch([str(workflow),'--',*sys.argv[1:]]))
