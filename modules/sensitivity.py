import numpy as np
import pandas as pd
from modules import model_tree


def calc_two_way_sensitivity(
    df: pd.DataFrame,
    node_id_x: str,
    range_x: tuple,
    node_id_y: str,
    range_y: tuple,
    steps: int = 5,
) -> pd.DataFrame:
    """2つの項目を同時に動かし、収支(ルート)がどう変化するかを格子状に計算する"""

    root_id = model_tree.find_root_id(df)

    x_values = np.linspace(range_x[0], range_x[1], steps)
    y_values = np.linspace(range_y[0], range_y[1], steps)

    result = np.zeros((steps, steps))

    for i, y_val in enumerate(y_values):
        for j, x_val in enumerate(x_values):
            df_temp = df.copy()
            df_temp.loc[df_temp["node_id"] == node_id_x, "value"] = x_val
            df_temp.loc[df_temp["node_id"] == node_id_y, "value"] = y_val
            calc_result = model_tree.calc_all(df_temp)
            root_value = calc_result.loc[calc_result["node_id"] == root_id, "calculated_value"].iloc[0]
            result[i, j] = root_value

    matrix_df = pd.DataFrame(
        result,
        index=[f"{v:,.1f}" for v in y_values],
        columns=[f"{v:,.1f}" for v in x_values],
    )
    return matrix_df
