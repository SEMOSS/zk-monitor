from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError
import sys


def explore_znode(zk, path):
    """Recursively explore ZooKeeper znodes starting from given path"""
    try:
        # Get children of current path
        children = zk.get_children(path)

        # Get data and stat of current node
        data, stat = zk.get(path)
        print(f"\nPath: {path}")
        print(f"Data: {data.decode('utf-8') if data else 'None'}")
        print(f"Stat: {stat}")

        # Recursively explore each child
        for child in children:
            child_path = path + "/" + child if path != "/" else "/" + child
            explore_znode(zk, child_path)

    except NoNodeError:
        print(f"Node {path} does not exist")
    except Exception as e:
        print(f"Error accessing {path}: {e}")


def main():
    # Connect to ZooKeeper
    zk = KazooClient(hosts="34.118.229.85:2181")
    try:
        zk.start()
        print("Successfully connected to ZooKeeper")

        # Start exploration from root and specifically check /sync
        explore_znode(zk, "/")
        explore_znode(zk, "/sync")

    except Exception as e:
        print(f"Failed to connect or explore: {e}")
    finally:
        zk.stop()
        zk.close()


if __name__ == "__main__":
    main()
