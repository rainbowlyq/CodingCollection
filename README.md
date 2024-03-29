# CodingCollection

## Function

批量自动处理、编译、运行、判定通过坚果云收件箱自动收集的cpp程序

## Basic Usage

### Step1

将通过坚果云收件箱自动收集的zip文件解压到collections目录下, 假设解压后的文件夹名为`code`，文件夹中的内容明明规则应当是`学号-姓名`

### Step2

将班级名单文件（含有`学号`和`姓名`列）重命名为`result.csv`，放置在项目根目录下

### Step3

运行命令行(`python processor.py [folder_name]`), 其中`folder_name`为**Step1**中解压后文件夹的名称， 例如：


```cmd
python processor.py code
```

## Advanced Usage

### Command Arguments

- `-h` or `--help`: 查看帮助信息
- `-i` or `--allow_identical_submission`: 将相同提交计入排名
- `-t` or `--allow_wrong_filetype`: 将错误文件名计为编译错误
- `-a` or `--allow_incorrect_answer`: 将错误输出计入排名
- `-r` or `--rank_only`: 只更新排名

### Recommended Workflow

先完整运行代码，根据`result.csv`中的判定结果进行检查和修改，然后通过`-r`命令重新更新排名
