@echo off
@chcp 65001

REM 切换到项目根目录
cd /d %~dp0..
python3 main.py -job True -init True
