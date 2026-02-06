#!/usr/bin/env python3
"""
Compare privacy defaults across graphistry versions.

Run this in each venv to detect whether privacy behavior changed:
    venv-0.44.1/bin/python scripts/compare_privacy_defaults.py
    venv-0.50.6/bin/python scripts/compare_privacy_defaults.py

Checks:
1. graphistry version
2. session.privacy default
3. PlotterBase._privacy default
4. cascade_privacy_settings() existence and hard-coded defaults
5. maybe_post_share_link() existence
6. graphistry.privacy() with no args behavior
7. plot() code path references to share_link
"""

import importlib
import inspect
import sys
import copy


def header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def check(label, value):
    print(f"  {label:.<50s} {value}")


def main():
    header("graphistry privacy defaults comparison")

    # 1. Version
    try:
        import graphistry
        check("graphistry version", graphistry.__version__)
    except Exception as e:
        check("graphistry version", f"ERROR: {e}")
        sys.exit(1)

    # 2. session.privacy default
    try:
        # Reset to get fresh state
        graphistry.register(api=3)
        session = graphistry.PyGraphistry._config
        # Try different attribute paths depending on version
        privacy_val = None
        for attr in ['privacy', '_privacy']:
            if hasattr(session, attr):
                privacy_val = getattr(session, attr)
                check(f"session.{attr} (default)", repr(privacy_val))
                break
        else:
            # Older versions may store config differently
            check("session.privacy", "attribute not found")

            # Check if there's a _config dict or similar
            if hasattr(graphistry, '_config'):
                cfg = graphistry._config
                check("graphistry._config type", type(cfg).__name__)
                if isinstance(cfg, dict) and 'privacy' in cfg:
                    check("graphistry._config['privacy']", repr(cfg['privacy']))
    except Exception as e:
        check("session.privacy", f"ERROR: {e}")

    # 3. PlotterBase._privacy default
    try:
        from graphistry.PlotterBase import PlotterBase
        # Look at __init__ signature or create instance
        src = inspect.getsource(PlotterBase.__init__)
        if '_privacy' in src:
            # Extract the default
            for line in src.split('\n'):
                if '_privacy' in line and '=' in line:
                    check("PlotterBase._privacy init line", line.strip())
                    break
        else:
            check("PlotterBase._privacy in __init__", "NOT FOUND")

        # Also check actual instance
        g = graphistry.edges(
            __import__('pandas').DataFrame({'s': [1], 'd': [2]}), 's', 'd'
        )
        check("g._privacy (instance)", repr(getattr(g, '_privacy', 'MISSING')))
    except ImportError:
        check("PlotterBase", "import failed (older version?)")
    except Exception as e:
        check("PlotterBase._privacy", f"ERROR: {e}")

    # 4. cascade_privacy_settings
    try:
        from graphistry.arrow_uploader import ArrowUploader
        if hasattr(ArrowUploader, 'cascade_privacy_settings'):
            check("cascade_privacy_settings()", "EXISTS")
            # Get the source to find hard-coded defaults
            src = inspect.getsource(ArrowUploader.cascade_privacy_settings)
            for line in src.split('\n'):
                stripped = line.strip()
                if 'mode =' in stripped and "'private'" in stripped:
                    check("  hard-coded default mode", stripped)
                if 'mode_action =' in stripped and ("'20'" in stripped or "'10'" in stripped):
                    check("  hard-coded default mode_action", stripped)
        else:
            check("cascade_privacy_settings()", "DOES NOT EXIST")
    except ImportError:
        check("arrow_uploader", "import failed")
    except Exception as e:
        check("cascade_privacy_settings", f"ERROR: {e}")

    # 5. maybe_post_share_link
    try:
        from graphistry.arrow_uploader import ArrowUploader
        if hasattr(ArrowUploader, 'maybe_post_share_link'):
            check("maybe_post_share_link()", "EXISTS")
            src = inspect.getsource(ArrowUploader.maybe_post_share_link)
            # Show the key conditional
            for line in src.split('\n'):
                stripped = line.strip()
                if 'session_privacy' in stripped or '_privacy' in stripped:
                    check("  key line", stripped)
        else:
            check("maybe_post_share_link()", "DOES NOT EXIST")
    except ImportError:
        check("maybe_post_share_link", "import failed")
    except Exception as e:
        check("maybe_post_share_link", f"ERROR: {e}")

    # 6. graphistry.privacy() with no args
    try:
        if hasattr(graphistry, 'privacy'):
            check("graphistry.privacy() method", "EXISTS")
            sig = inspect.signature(graphistry.privacy)
            check("  signature", str(sig))

            # Check what calling with no args does
            try:
                graphistry.privacy()
                # Check session state after
                session = graphistry.PyGraphistry._config
                for attr in ['privacy', '_privacy']:
                    if hasattr(session, attr):
                        val = getattr(session, attr)
                        check(f"  after privacy(): session.{attr}", repr(val))
                        break
            except TypeError as e:
                check("  privacy() no-args call", f"TypeError: {e}")
        else:
            check("graphistry.privacy()", "DOES NOT EXIST")
    except Exception as e:
        check("graphistry.privacy()", f"ERROR: {e}")

    # 7. plot() references to share_link / privacy
    try:
        from graphistry.PlotterBase import PlotterBase
        if hasattr(PlotterBase, 'plot'):
            src = inspect.getsource(PlotterBase.plot)
            has_share = 'share_link' in src or 'maybe_post_share_link' in src
            has_privacy = 'privacy' in src or '_privacy' in src
            check("plot() references share_link", str(has_share))
            check("plot() references privacy", str(has_privacy))
            if has_share:
                for line in src.split('\n'):
                    if 'share_link' in line or 'maybe_post_share_link' in line:
                        check("  line", line.strip())
        else:
            check("PlotterBase.plot()", "NOT FOUND")
    except Exception as e:
        check("plot() inspection", f"ERROR: {e}")

    # 8. Check if privacy module exists
    try:
        from graphistry import privacy as priv_mod
        check("graphistry.privacy module", "EXISTS")
        if hasattr(priv_mod, 'Mode'):
            check("  Mode type", repr(priv_mod.Mode))
        if hasattr(priv_mod, 'Privacy'):
            check("  Privacy type", repr(priv_mod.Privacy))
    except ImportError:
        check("graphistry.privacy module", "DOES NOT EXIST (older version)")

    header("DONE")


if __name__ == "__main__":
    main()
