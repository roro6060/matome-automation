import pickle


def save_as_pickle(path, data):
    with open(path, mode="wb") as f:
        pickle.dump(data, f)


def load_from_pickle(path):
    with open("path", mode="rb") as f:
        data = pickle.load(f)

    return data
