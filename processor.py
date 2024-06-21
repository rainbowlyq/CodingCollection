# -*- coding: utf-8 -*-
"""
@File    : processor.py
@Time    : 2024/3/8 14:32
@Author  : lyq
"""
import argparse
import hashlib
import logging
import os
import shutil
import sys
from functools import cached_property
import subprocess
import threading

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stderr), logging.FileHandler('console.log')])
logger = logging.getLogger(__name__)


def main():
    args = get_args()
    logger.info(f"Processing project: {args['project']}")
    p = Processor(**args)
    if not args['rank_only']:
        p.init_files()
        p.generate_and_run_bat()
    if args['update_answer'] or not args['rank_only']:
        p.update_results()
    p.update_ranks()


class Processor:
    def __init__(self, project: str, **kwargs):
        self.project = project
        self.folders = {
            "base": os.path.join(".", project),
            "dll": os.path.join(".", "dll"),
            "original": os.path.join(".", "collections", project),
            'answers': os.path.join(".", "answers"),
            'collection': os.path.join(".", project, 'collection'),
            'source': os.path.join(".", project, 'source'),
            'bin': os.path.join(".", project, 'bin'),
            'output': os.path.join(".", project, 'output')
        }
        self.answer_file = os.path.join(self.folders['answers'], project + ".txt")
        self.md5_dict = {}
        supported_configs = ["allow_identical_submission", "allow_wrong_filetype", "allow_incorrect_answer"]
        self.config = {config_name: kwargs.get(config_name, False) for config_name in supported_configs}
        self.result_df = self._read_result()

    def generate_and_run_bat(self):
        logger.info("Generating and running bat file")
        with open("run_template.bat", "r", encoding='utf-8') as template:
            lines = template.readlines()
        edited_lines = []
        # generate bat from template by replacing `$$keyword$$`
        for line in lines:
            if "$$" in line:
                line = line.replace("$$BIN_FOLDER$$", self.folders["bin"])
                line = line.replace("$$SOURCE_FOLDER$$", self.folders["source"])
                line = line.replace("$$OUTPUT_FOLDER$$", self.folders["output"])
            edited_lines.append(line)
        with open("run.bat", "w", encoding='utf-8') as bat:
            bat.writelines(edited_lines)
        # 把dll文件夹中的所有文件移动到bin文件夹中
        for file in os.listdir(self.folders['dll']):
            shutil.copy(os.path.join(self.folders['dll'], file), self.folders["bin"])
        # compile all files
        os.system(f"run.bat 1> {os.path.join(self.folders['base'], 'log.txt')} 2>&1")
        # run all exe
        for filename in os.listdir(self.folders["bin"]):
            if filename.endswith(".exe"):
                cmd = [f'{os.path.join(self.folders["bin"], filename)}']
                run_with_timeout(cmd, os.path.join(self.folders["output"], filename.replace(".exe", ".txt")))
        # 删除bin文件夹中的所有dll文件
        for dll_file in os.listdir(self.folders["bin"]):
            if dll_file.endswith(".dll"):
                os.remove(os.path.join(self.folders["bin"], dll_file))

    def init_files(self):
        # remove existing files
        if os.path.exists(self.folders['base']):
            shutil.rmtree(self.folders['base'])
        # copy files from collections
        shutil.copytree(self.folders['original'], self.folders["collection"])
        # make directories
        for folder in self.folders.values():
            if not os.path.exists(folder):
                os.makedirs(folder)
        # process all collected files
        for path in os.listdir(self.folders['collection']):
            full_path = os.path.join(self.folders['collection'], path)
            if os.path.isdir(full_path):
                # get the latest cpp file from a directory
                filename = self._get_latest_filename(path)
                latest_filepath = os.path.join(full_path, filename)
                if filename.endswith(".cpp"):
                    target_filename = '-'.join(self._get_student_info(path)) + '.cpp'
                    target_filepath = os.path.join(self.folders['source'], target_filename)
                    self._update_md5(latest_filepath, path)
                    shutil.copy(latest_filepath, target_filepath)
                    remove_pause(target_filepath)
                else:
                    self._set_wrong_filetype(*os.path.splitext(filename))
            elif full_path.endswith(".xlsx"):
                # process submission.xlsx
                self._process_submission(full_path)
            elif full_path.endswith(".cpp"):
                # process cpp files
                self._update_md5(full_path, path.split('.cpp')[0])
                remove_pause(full_path)
                target_filename = '-'.join(self._get_student_info(path)) + '.cpp'
                shutil.copy(full_path, os.path.join(self.folders['source'], target_filename))
            else:
                self._set_wrong_filetype(*os.path.splitext(path))

    def update_results(self):
        logger.info("Updating results")
        if f"{self.project}_result" in self.result_df.columns:
            self.result_df.drop(columns=[f"{self.project}_result"], inplace=True)
        cpp_files = set(file.split(".cpp")[0] for file in os.listdir(self.folders["source"]))
        exe_files = set(file.split(".exe")[0] for file in os.listdir(self.folders["bin"]))
        txt_files = set(file.split(".txt")[0] for file in os.listdir(self.folders["output"]))
        wrong_answer_filenames = set()
        for filename in txt_files:
            # read output
            with open(os.path.join(self.folders["output"], filename + ".txt"), "r") as f:
                output = f.read()
            if not self.is_correct_answer(output):
                wrong_answer_filenames.add(filename)
        results = {
            "CompileError": cpp_files - exe_files,  # 如果有cpp，没有exe，标记为编译失败
            "RuntimeError": exe_files - txt_files,  # 如果有exe，没有output，标记为运行失败
            "IncorrectAnswer": wrong_answer_filenames  # 如果有output，但是内容不对，标记为答案错误
        }
        submission_col = f"{self.project}_submission"  # 记录最后提交时间
        result_col = f"{self.project}_result"  # 记录提交判定结果
        for index, row in self.submission_df.iterrows():
            self.result_df.loc[index, submission_col] = row['submit_time']
        for error_type, filenames in results.items():
            for filename in filenames:
                student_id, name = self._get_student_info(filename)
                self.result_df.loc[student_id, result_col] = error_type
        self.result_df.loc[self.result_df[submission_col].isna(), result_col] = "NoSubmission"
        self.result_df.to_csv("results.csv")
        self.result_df.to_excel("results.xlsx")

    def is_correct_answer(self, output) -> bool:
        # check whether the required output contents are in the output file
        output = output.strip().lower()
        # return self.correct_answer[-1] not in output:
        required_lines = [line.strip() for line in self.correct_answer if not line.startswith('[')]
        required_true = all(required_line in output for required_line in required_lines)

        optional_lines = [line.strip() for line in self.correct_answer if line.startswith('[')]
        optional_groups = [line.split(']')[0] for line in optional_lines]
        optional_true = len(optional_lines) == 0
        for group in optional_groups:
            optional_true = False
            for line in [line for line in optional_lines if line.startswith(group)]:
                if line.split(']')[1] in output.replace('\n', ' '):
                    optional_true = True
                    break
        return required_true and optional_true

    def update_ranks(self):
        ranked_mask = ~pd.to_numeric(self.result_df[f"{self.project}_result"], errors='coerce').isna()
        empty_mask = self.result_df[f"{self.project}_result"].isna()
        rank_candidates_mask = (empty_mask | ranked_mask)
        rank = self.result_df[f"{self.project}_submission"][rank_candidates_mask].rank().astype(int)
        self.result_df.loc[rank_candidates_mask, f"{self.project}_result"] = rank
        self.result_df.to_csv("results.csv")
        self.result_df.to_excel("results.xlsx")
        logger.info(f"Ranks updated, {len(rank)} students are ranked. ")

    def _get_latest_filename(self, dir_path):
        student_id, name = self._get_student_info(dir_path)
        assert self.submission_df.loc[student_id, 'name'] == name
        return self.submission_df.loc[student_id, 'filename']

    def _update_md5(self, filepath, info):
        md5 = calculate_md5(filepath)
        if self.md5_dict.get(md5) is None:
            self.md5_dict[md5] = info
        else:
            other = self.md5_dict[md5]
            logger.warning(f"Identical submissions: {info} with {other}")
            if not self.config['allow_identical_submission']:
                res_col = f"{self.project}_result"
                self.result_df.loc[self._get_student_info(info)[0], res_col] = "IdenticalSubmission"
                self.result_df.loc[self._get_student_info(other)[0], res_col] = "IdenticalSubmission"

    def _set_wrong_filetype(self, filename, ext):
        logger.warning(f"Wrong filetype: {filename}{ext}")
        if not self.config['allow_wrong_filetype']:
            student_id, name = self._get_student_info(filename)
            self.result_df.loc[student_id, f"{self.project}_result"] = "WrongFileType"

    def _process_submission(self, filepath):
        submission = pd.read_excel(filepath, sheet_name='提交清单', dtype={'学号': str},
                                   usecols=['姓名', '学号', '文件名', '提交时间'])
        submission.rename(
            columns={'姓名': 'name', '学号': 'student_id', '文件名': 'filename', '提交时间': 'submit_time'},
            inplace=True)
        submission.drop_duplicates(subset=['name', 'student_id'], keep='first', inplace=True)
        submission.set_index('student_id', inplace=True)
        submission.to_csv(os.path.join(self.folders['base'], "submission.csv"))
        return submission

    def _get_student_info(self, file, validate=True) -> tuple[str, str]:
        """return student_id and name"""
        filename, ext = os.path.splitext(file)
        student_id, name = filename.split('-')
        if validate:
            if student_id in self.result_df.index:
                true_name = self.result_df.loc[student_id, '姓名']
                if true_name != name:
                    logger.warning(f"姓名-学号不匹配, {filename}, {true_name}, {name}")
                    self.submission_df.loc[student_id, 'name'] = true_name
                    self.submission_df.to_csv(os.path.join(self.folders['base'], "submission.csv"))
                    name = true_name
            else:
                if name in self.result_df['姓名'].values:
                    logger.warning(f"学号错误, {name}, {student_id}")
                    student_id = self.result_df[self.result_df['姓名'] == name].index[0]
                    df = self.submission_df[self.submission_df['name'] == name].sort_values("submit_time")
                    if len(df) > 1:
                        # keep the latest submission
                        self.submission_df.drop(df.iloc[:-1].index, inplace=True)
                    self.submission_df.loc[self.submission_df['name'] == name].index = [student_id]
                    self.submission_df.to_csv(os.path.join(self.folders['base'], "submission.csv"))
                else:
                    logger.warning(f"学号姓名不存在, {student_id}, {name}")
                    self.result_df.loc[student_id, '姓名'] = name
        return student_id, name

    def _read_result(self):
        result_df = pd.read_csv("results.csv", index_col='学号', dtype={'学号': str, '序号': str, '年级': str})
        # result_df[f"{self.project}_submission"] = None
        # result_df[f"{self.project}_result"] = None
        return result_df

    @cached_property
    def correct_answer(self) -> list[str]:
        try:
            with open(self.answer_file, "r") as f:
                return f.readlines()
        except FileNotFoundError:
            # correct_answer = input("请输入正确答案：")
            # with open(os.path.join(self.answer_file), "w") as f:
            #     f.write(correct_answer)
            # return [correct_answer]
            print("请在下方输入正确答案（按Ctrl+D结束输入）：")
            correct_answer = sys.stdin.readlines()
            # remove empty lines
            correct_answer = [line.lower() for line in correct_answer if line.strip()]
            with open(self.answer_file, "w") as f:
                f.writelines(correct_answer)
            return correct_answer

    @cached_property
    def submission_df(self):
        processed = os.path.join(self.folders['base'], "submission.csv")
        return pd.read_csv(processed, dtype={'student_id': str}, index_col=0)


def calculate_md5(file_path):
    with open(file_path, "rb") as f:
        content = f.read()
    md5_hash = hashlib.md5(content).hexdigest()
    return md5_hash


def remove_pause(source_filepath):
    try:
        with open(source_filepath, "r", encoding='utf-8') as source:
            lines = source.readlines()
    except UnicodeDecodeError:
        with open(source_filepath, "r", encoding='gbk') as source:
            lines = source.readlines()
    edited_lines = []
    has_algorithm = False
    for line in lines:
        if 'include' in line and 'algorithm' in line:
            has_algorithm = True
        line = line.replace('system("pause");', '')
        line = line.replace('system ("pause");', '')
        line = line.replace('getchar()', '')
        edited_lines.append(line)
    if not has_algorithm:
        edited_lines = [edited_lines[0]] + ["#include<algorithm>\n"] + edited_lines[1:]
    with open(source_filepath, "w", encoding='utf-8') as source:
        source.writelines(edited_lines)


def get_args() -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=str, nargs='?',
                        help='The folder name of the collected codes(should be in directory `[project]/collections/`)')
    parser.add_argument('-i', '--allow_identical_submission', action='store_true', help='Allow identical submissions')
    parser.add_argument('-t', '--allow_wrong_filetype', action='store_true', help='Allow wrong filetype')
    parser.add_argument('-a', '--allow_incorrect_answer', action='store_true', help='Allow incorrect answer')
    parser.add_argument('-r', '--rank_only', action='store_true', help='Only update ranks')
    parser.add_argument('-u', '--update_answer', action='store_true', help='Update correct answer and ranks')
    args = vars(parser.parse_args())
    if args.get('project') is None:
        args['project'] = input("Please input the project name: ")
    assert os.path.exists(os.path.join("collections", args['project'])), "Invalid project name"
    return args


def run_with_timeout(cmd: list[str], output_filepath, timeout_seconds=2):
    # Open the output file
    with open(output_filepath, 'w') as f:
        # Start the subprocess
        process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.PIPE)

        # Define a thread to wait for the process to complete
        def target():
            try:
                process.communicate()
            except subprocess.TimeoutExpired:
                pass

        # Start the thread
        thread = threading.Thread(target=target)
        thread.start()

        # Wait for the timeout duration
        thread.join(timeout_seconds)

        # If the thread is still alive after the timeout, kill the process
        if thread.is_alive():
            process.kill()
            f.write(f"Process {process.pid} is killed after {timeout_seconds} seconds timeout.\n")
            thread.join()
            return 2

        return process.returncode


if __name__ == '__main__':
    main()
