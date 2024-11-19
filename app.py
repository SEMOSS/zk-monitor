import streamlit as st
import logging
import pandas as pd
from kazoo.client import KazooClient
from datetime import datetime
from config import model_config, ZK_HOST

MODEL_ID_TO_NAME = {model["model_id"]: model["model_name"] for model in model_config}
MODEL_ID_TO_REPO = {
    model["model_id"]: model["model_repo_name"] for model in model_config
}


def setup_zk():
    """Setup ZooKeeper connection"""
    try:
        zk = KazooClient(hosts=ZK_HOST)
        zk.start()
        return zk
    except Exception as e:
        st.error(f"Failed to connect to ZooKeeper: {e}")
        return None


def remove_model(zk, path, model_id):
    """Remove a model from the specified ZooKeeper path"""
    try:
        full_path = f"{path}/{model_id}"
        if zk.exists(full_path):
            zk.delete(full_path)
            st.success(
                f"Successfully removed model {MODEL_ID_TO_NAME.get(model_id, model_id)}"
            )
            return True
    except Exception as e:
        st.error(f"Failed to remove model: {e}")
    return False


def get_model_info(zk, path):
    """Get model IDs and their cluster IPs from a specific path"""
    models = []
    if zk.exists(path):
        model_ids = zk.get_children(path)
        for model_id in model_ids:
            full_path = f"{path}/{model_id}"
            data, stat = zk.get(full_path)
            models.append(
                {
                    "model_id": model_id,
                    "model_name": MODEL_ID_TO_NAME.get(model_id, "Unknown Model"),
                    "model_repo": MODEL_ID_TO_REPO.get(model_id, "Unknown Repo"),
                    "cluster_ip": data.decode("utf-8"),
                    "last_updated": datetime.fromtimestamp(stat.mtime / 1000).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )
    return models


def display_model_table(zk, models, status, path):
    """Display a table of models with removal buttons"""
    if not models:
        st.info(f"No {status.lower()} models found")
        return

    df = pd.DataFrame(models)

    for idx, row in df.iterrows():
        col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 3, 2, 2, 1])
        with col1:
            st.write(row["model_name"])
        with col2:
            st.write(row["model_id"])
        with col3:
            st.write(row["model_repo"])
        with col4:
            st.write(row["cluster_ip"])
        with col5:
            st.write(row["last_updated"])
        with col6:
            if st.button(
                "🗑️",
                key=f"remove_{status}_{row['model_id']}",
                help=f"Remove {row['model_name']}",
            ):
                if remove_model(zk, path, row["model_id"]):
                    st.rerun()

    st.info(f"Found {len(models)} {status.lower()} models")


def main():
    logging.basicConfig(level=logging.INFO)
    st.set_page_config(page_title="Model Status Monitor", page_icon="🔍", layout="wide")
    st.title("Model Status Monitor")

    zk = setup_zk()
    if zk:
        try:
            with st.sidebar:
                st.header("Controls")
                if st.button("🔄 Refresh Data"):
                    st.rerun()

            # Warming Models
            st.header("🔸 Warming")
            warming_models = get_model_info(zk, "/models/warming")
            display_model_table(zk, warming_models, "Warming", "/models/warming")

            st.markdown("---")

            # Active Models
            st.header("✅ Active")
            active_models = get_model_info(zk, "/models/active")
            display_model_table(zk, active_models, "Active", "/models/active")

            st.markdown("---")

            # Model Details
            st.header("📊 Model Details")
            tabs = st.tabs(["All Models", "Path Explorer"])

            with tabs[0]:
                all_models = []
                for model in warming_models:
                    model["status"] = "Warming"
                    all_models.append(model)
                for model in active_models:
                    model["status"] = "Active"
                    all_models.append(model)

                if all_models:
                    df_all = pd.DataFrame(all_models)
                    st.dataframe(
                        df_all,
                        column_config={
                            "model_name": st.column_config.TextColumn(
                                "Model Name", help="Name of the model", width="medium"
                            ),
                            "model_id": st.column_config.TextColumn(
                                "Model ID", help="UUID of the model", width="medium"
                            ),
                            "model_repo": st.column_config.TextColumn(
                                "Repository", help="Model repository", width="medium"
                            ),
                            "cluster_ip": "Cluster IP",
                            "status": st.column_config.SelectboxColumn(
                                "Status",
                                help="Current model status",
                                width="medium",
                                options=["Active", "Warming"],
                            ),
                            "last_updated": "Last Updated",
                        },
                        hide_index=True,
                    )
                else:
                    st.info("No models found in ZooKeeper")

            with tabs[1]:
                path_to_check = st.text_input(
                    "Enter ZooKeeper path to explore", "/models"
                )
                if st.button("Explore Path"):
                    if zk.exists(path_to_check):
                        children = zk.get_children(path_to_check)
                        st.success(f"Found {len(children)} items at {path_to_check}")
                        for child in children:
                            full_path = f"{path_to_check}/{child}"
                            data, stat = zk.get(full_path)
                            model_name = MODEL_ID_TO_NAME.get(child, "Unknown Model")
                            st.code(f"{model_name} ({child}): {data.decode('utf-8')}")
                    else:
                        st.warning(f"Path {path_to_check} doesn't exist")

        except Exception as e:
            st.error(f"Error while accessing ZooKeeper: {e}")
        finally:
            zk.stop()
    else:
        st.error(
            "Failed to connect to ZooKeeper. Please check if ZooKeeper is running on localhost:2181"
        )


if __name__ == "__main__":
    main()
