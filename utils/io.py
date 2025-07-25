import pandas as pd

from typing import List


class CsvReader:
    def __init__(self, index_label: str):
        self.index_label = index_label

    def read_df(self, path: str) -> pd.DataFrame:
        skip_rows = 0
        with open(path, 'r') as file:
            for line in file:
                line = line.strip()
                if line.startswith('#') or line.startswith("\"#"):
                    skip_rows += 1
                else:
                    break

        df = pd.read_csv(path, skiprows=skip_rows, index_col=self.index_label)
        return df


class CsvWriter:
    def __init__(
            self,
            index: List[str],
            columns: List[str],
            index_label: str,
            comments: List[str]
        ):
        self.index = index
        self.columns = columns
        self.index_label = index_label
        self.comments = comments

    def init_df(self) -> pd.DataFrame:
        results = pd.DataFrame(index=self.index, columns=self.columns)
        results.index.name = self.index_label
        return results

    def write_df(
            self,
            df: pd.DataFrame,
            path: str,
        ) -> None:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            for comment in self.comments:
                if ',' in comment:
                    f.write(f'"# {comment}"\n')
                else:
                    f.write(f'# {comment}\n')
            df.to_csv(f, index_label=self.index_label, index=True)