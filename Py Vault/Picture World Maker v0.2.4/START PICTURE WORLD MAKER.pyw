from pathlib import Path
import sys
sys.dont_write_bytecode = True
system_files = Path(__file__).resolve().parent  # v0.2.2: lives inside System Files
sys.path.insert(0, str(system_files))
from PICTURE_WORLD_MAKER import main
raise SystemExit(main())
