@echo off
chcp 65001
setlocal enabledelayedexpansion

rem 设置编译后的exe存放路径
set "BIN_FOLDER=$$BIN_FOLDER$$"

rem 设置源代码文件夹路径
set "SOURCE_FOLDER=$$SOURCE_FOLDER$$"

rem 设置输出txt路径
set "OUTPUT_FOLDER=$$OUTPUT_FOLDER$$"

rem 确保输出文件夹存在
if not exist "%BIN_FOLDER%" mkdir "%BIN_FOLDER%"
if not exist "%SOURCE_FOLDER%" mkdir "%SOURCE_FOLDER%"
if not exist "%OUTPUT_FOLDER%" mkdir "%OUTPUT_FOLDER%"

rem 遍历源代码文件夹中的所有cpp文件
for %%f in ("%SOURCE_FOLDER%\*.cpp") do (
    rem 获取当前cpp文件的文件名（不含扩展名）
    set "filename=%%~nf"
    
    rem 编译当前cpp文件成exe
    g++ !SOURCE_FOLDER!\!filename!.cpp -o !BIN_FOLDER!\!filename!.exe -w

    rem 检查编译是否成功，如果成功则打印消息，否则打印错误信息
    if !errorlevel! equ 0 (
        echo !filename!.cpp 编译成功！
    ) else (
        echo !filename!.cpp 编译失败！
    )
)

rem 遍历输出文件夹中的所有exe文件
for %%f in ("%BIN_FOLDER%\*.exe") do (
    rem 获取当前cpp文件的文件名（不含扩展名）
    set "filename=%%~nf"
    
    rem 编译当前cpp文件成exe
    !BIN_FOLDER!\!filename!.exe >!OUTPUT_FOLDER!\!filename!.txt

    rem 检查编译是否成功，如果成功则打印消息，否则打印错误信息
    if !errorlevel! equ 0 (
        echo !filename!.exe 运行成功！
    ) else (
        echo !filename!.exe 运行失败！
    )
)

endlocal