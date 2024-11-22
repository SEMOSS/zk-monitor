import streamlit as st
import logging
import pandas as pd
import json
from kazoo.client import KazooClient
from datetime import datetime
from config import ZK_HOST


def setup_zk():
    """Setup ZooKeeper connection"""
    try:
        print(f"Connecting to ZooKeeper at {ZK_HOST}")
        zk = KazooClient(hosts=ZK_HOST)
        zk.start()
        return zk
    except Exception as e:
        st.error(f"Failed to connect to ZooKeeper on {ZK_HOST}: {e}")
        return None


def remove_model(zk, path, model_id):
    """Remove a model from the specified ZooKeeper path"""
    try:
        full_path = f"{path}/{model_id}"
        if zk.exists(full_path):
            # Get model name before deleting for the success message
            data, _ = zk.get(full_path)
            try:
                model_data = json.loads(data.decode("utf-8"))
                model_name = model_data.get("model_name", model_id)
            except json.JSONDecodeError:
                model_name = model_id

            zk.delete(full_path)
            st.success(f"Successfully removed model {model_name}")
            return True
    except Exception as e:
        st.error(f"Failed to remove model: {e}")
    return False


def get_model_info(zk, path):
    """Get model IDs and their information from a specific path"""
    models = []
    if zk.exists(path):
        model_ids = zk.get_children(path)
        for model_id in model_ids:
            full_path = f"{path}/{model_id}"
            data, stat = zk.get(full_path)
            try:
                # Try to parse the JSON data
                model_data = json.loads(data.decode("utf-8"))
                models.append(
                    {
                        "model_id": model_id,
                        "model_name": model_data.get("model_name", "Unknown Model"),
                        "cluster_ip": model_data.get("ip", "N/A"),
                        "last_updated": datetime.fromtimestamp(
                            stat.mtime / 1000
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            except json.JSONDecodeError:
                # Fallback for legacy format (just IP address)
                models.append(
                    {
                        "model_id": model_id,
                        "model_name": "Unknown Model",
                        "cluster_ip": data.decode("utf-8"),
                        "last_updated": datetime.fromtimestamp(
                            stat.mtime / 1000
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
    return models


def get_deployer_status(zk):
    """Get the model deployer service status and IP"""
    deployer_path = "/services/kube-model-deployer"
    try:
        if zk.exists(deployer_path):
            data, stat = zk.get(deployer_path)
            return {
                "status": "Active",
                "ip_address": data.decode("utf-8"),
                "last_updated": datetime.fromtimestamp(stat.mtime / 1000).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }
        return {
            "status": "Not Found",
            "ip_address": "N/A",
            "last_updated": "N/A",
        }
    except Exception as e:
        logging.error(f"Error getting deployer status: {e}")
        return {
            "status": "Error",
            "ip_address": "N/A",
            "last_updated": "N/A",
        }


def display_model_table(zk, models, status, path):
    """Display a table of models with removal buttons"""
    if not models:
        st.info(f"No {status.lower()} models found")
        return

    df = pd.DataFrame(models)

    # Updated column layout - removed model_repo
    for idx, row in df.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 1])
        with col1:
            st.write(row["model_name"])
        with col2:
            st.write(row["model_id"])
        with col3:
            st.write(row["cluster_ip"])
        with col4:
            st.write(row["last_updated"])
        with col5:
            if st.button(
                "🗑️",
                key=f"remove_{status}_{row['model_id']}",
                help=f"Remove {row['model_name']}",
            ):
                if remove_model(zk, path, row["model_id"]):
                    st.rerun()

    st.info(f"Found {len(models)} {status.lower()} models")


def display_deployer_status(deployer_info):
    """Display the model deployer service status"""
    container = st.container()
    container.markdown(
        """
        <style>
            [data-testid="stVerticalBlock"] div:has(> [data-testid="stVerticalBlock"]) {
                background-color: #f8f9fa;
                padding: 1rem;
                border-radius: 0.5rem;
                border: 1px solid #e9ecef;
                margin-bottom: 1rem;
            }
            .status-label {
                font-size: 0.875rem;
                color: #6c757d;
                margin-bottom: 0.25rem;
                font-weight: 400;
            }
            .status-value {
                font-size: 1rem;
                font-weight: 500;
                color: #212529;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    with container:

        status_col, ip_col, time_col = st.columns([1, 2, 2])

        with status_col:
            st.markdown('<p class="status-label">Status</p>', unsafe_allow_html=True)
            if deployer_info["status"] == "Active":
                st.markdown(
                    '🟢 <span class="status-value">Active</span>',
                    unsafe_allow_html=True,
                )
            elif deployer_info["status"] == "Not Found":
                st.markdown(
                    '🟡 <span class="status-value">Not Found</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '🔴 <span class="status-value">Error</span>', unsafe_allow_html=True
                )

        with ip_col:
            st.markdown(
                '<p class="status-label">IP Address</p>', unsafe_allow_html=True
            )
            ip_display = deployer_info["ip_address"]
            st.markdown(
                f'<p class="status-value">{ip_display}</p>', unsafe_allow_html=True
            )

        with time_col:
            st.markdown(
                '<p class="status-label">Last Updated</p>', unsafe_allow_html=True
            )
            time_display = deployer_info["last_updated"]
            st.markdown(
                f'<p class="status-value">{time_display}</p>', unsafe_allow_html=True
            )


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

            # Model Deployer Status
            st.header("🚀 Model Deployer Status")
            deployer_info = get_deployer_status(zk)
            display_deployer_status(deployer_info)

            st.markdown("---")

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
                            try:
                                model_data = json.loads(data.decode("utf-8"))
                                model_name = model_data.get(
                                    "model_name", "Unknown Model"
                                )
                                st.code(
                                    f"{model_name} ({child}): {json.dumps(model_data, indent=2)}"
                                )
                            except json.JSONDecodeError:
                                st.code(
                                    f"Unknown Model ({child}): {data.decode('utf-8')}"
                                )
                    else:
                        st.warning(f"Path {path_to_check} doesn't exist")

        except Exception as e:
            st.error(f"Error while accessing ZooKeeper: {e}")
        finally:
            zk.stop()
    else:
        st.error(
            f"Failed to connect to ZooKeeper. Please check if ZooKeeper is running on {ZK_HOST}"
        )


if __name__ == "__main__":
    main()
