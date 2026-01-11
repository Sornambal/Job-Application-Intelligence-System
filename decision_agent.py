import pandas as pd
from datetime import datetime

def decide_and_update(data, excel_path):
    try:
        df = pd.read_excel(excel_path)
    except:
        df = pd.DataFrame(columns=[
            "Company", "Role", "Status", "Last Update"
        ])

    match = df[
        (df["Company"] == data["company"]) &
        (df["Role"] == data["role"])
    ]

    now = datetime.now().strftime("%Y-%m-%d")

    if match.empty:
        df.loc[len(df)] = [
            data["company"],
            data["role"],
            data["status"],
            now
        ]
        action = "Inserted"
    else:
        idx = match.index[0]
        df.at[idx, "Status"] = data["status"]
        df.at[idx, "Last Update"] = now
        action = "Updated"

    df.to_excel(excel_path, index=False)
    return action
