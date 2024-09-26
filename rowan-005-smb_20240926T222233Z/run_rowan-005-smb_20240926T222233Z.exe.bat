@echo off
        cd /d %~dp0\..
        IF EXIST "rowan-005-smb_20240926T222233Z.exe" (
            IF EXIST "rowan-005-smb.parquet" (
                start rowan-005-smb_20240926T222233Z.exe ./rowan-005-smb.parquet
            ) ELSE (
                echo Parquet file not found: rowan-005-smb.parquet
                pause
            )
        ) ELSE (
            echo Executable not found: rowan-005-smb_20240926T222233Z.exe
            pause
        )
        