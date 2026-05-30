METHOD = {
    "transformer",
    "cnn",
    "gan",
    "federated",
    "diffusion",
    "bert"
}

TASK = {
    "classification",
    "segmentation",
    "detection",
    "prediction"
}

DATASET = {
    "mimic",
    "imagenet",
    "chexpert"
}

METRIC = {
    "accuracy",
    "dice",
    "auc",
    "f1"
}

DOMAIN = {
    "radiology",
    "pathology",
    "medical imaging",
    "healthcare"
}

CONSTRAINT = {
    "privacy",
    "fairness",
    "low resource"
}


def classify_entity(concept):

    c = concept.lower()

    for x in METHOD:
        if x in c:
            return "METHOD"

    for x in TASK:
        if x in c:
            return "TASK"

    for x in DATASET:
        if x in c:
            return "DATASET"

    for x in METRIC:
        if x in c:
            return "METRIC"

    for x in DOMAIN:
        if x in c:
            return "DOMAIN"

    for x in CONSTRAINT:
        if x in c:
            return "CONSTRAINT"

    return "SCIENTIFIC_CONCEPT"