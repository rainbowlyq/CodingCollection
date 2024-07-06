# CodingCollection

## Function

批量自动处理、编译、运行、判定通过坚果云收件箱自动收集的cpp程序

## Basic Usage

### Step1

将通过坚果云收件箱自动收集的zip文件解压到collections目录下, 假设解压后的文件夹名为`code`，文件夹中的内容命名规则应当是`学号-姓名`

### Step2

将班级名单文件（含有`学号`和`姓名`列）重命名为`result.csv`，放置在项目根目录下

### Step3

运行命令行(`python processor.py [folder_name]`), 其中`folder_name`为**Step1**中解压后文件夹的名称， 例如：

```cmd
python processor.py code
```

### Step4

根据命令行提示输入正确答案，支持多行输入，输入完成后按`Ctrl+D`结束输入

> #### Tips
> 
> - 正确答案判定规则为：只要正确答案中的每一行都出现在程序输出中，则判定为正确
> - 对于多种答案（满足其中任一即可），使用前置`[group]`表示group中的答案出现任一即可
>
>   - 示例：如果`1 2 3`和`1,2,3`均为正确答案，则正确答案可以设置为：
>   ```
>   [group1]1 2 3
>   [group1]1,2,3
>   ```

### Step5

运行`streamlit run query.py`或`python -m streamlit run query.py`以查询个人成绩

## Advanced Usage

### Command Arguments

- `-h` or `--help`: 查看帮助信息
- `-i` or `--allow_identical_submission`: 将相同提交计入排名
- `-t` or `--allow_wrong_filetype`: 将错误文件名计为编译错误
- `-a` or `--allow_incorrect_answer`: 将错误输出计入排名
- `-r` or `--rank_only`: 只更新排名
- `-u` or `--update_answer`: 重新评阅答案并更新排名

### Recommended Workflow

- 先完整运行代码，根据`result.csv`中的判定结果更新正确答案，然后通过`-u`命令重新评阅答案并更新排名（注：结果可复现，推荐）
- 先完整运行代码，根据`result.csv`中的判定结果进行检查和修改，然后通过`-r`命令重新更新排名（注：如果重新完整运行代码，会覆盖人工修改的结果）

## Todo List

- [x] 增加仅重新评阅答案功能
- [x] 支持多种正确答案
- [x] 支持超时判定与处理
- [ ] 使用python并行编译运行cpp代码，记录相关信息
- [ ] 打印仅结果错误的输出/代码，人工判断是否正确