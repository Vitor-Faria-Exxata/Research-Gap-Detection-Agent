TOP_PAPERS = 50

EMBEDDING_MODEL = (
    "allenai/specter2_base"
)

#
# graph + hypotheses
#

MIN_SIMILARITY = 0.75

MIN_EDGE_WEIGHT = 1

MAX_PATH_LENGTH = 3

MIN_COMMUNITY_SIZE = 10

MAX_HUB_DEGREE = 45

MAX_NEIGHBORS_PER_HUB = 20

#
# concept filtering
#

MAX_CONCEPTS_PER_PAPER = 30

MAX_DOC_FREQ_RATIO = 0.35

MIN_CONCEPT_LENGTH = 2

MAX_CONCEPT_TOKENS = 5

MIN_IDF = 1.2

#
# embeddings
#

EMBEDDING_BATCH_SIZE = 64

#
# scientific entities
#

VALID_ENTITY_LABELS = {
    "METHOD",
    "TASK",
    "DATASET",
    "METRIC",
    "DOMAIN",
    "CONSTRAINT",
    "MODEL",
    "ARCHITECTURE",
    "PROBLEM",
    "SCIENTIFIC_CONCEPT"
}

#
# generic concepts
#

GENERIC_TERMS = {

    #
    # academic rhetoric
    #

    "research",
    "study",
    "paper",
    "article",
    "analysis",
    "review",
    "results",
    "discussion",
    "future work",
    "future research",
    "future direction",
    "conclusion",
    "limitations",
    "finding",
    "findings",

    #
    # generic ML
    #

    "method",
    "methods",
    "approach",
    "framework",
    "model",
    "models",
    "system",
    "systems",
    "technique",
    "techniques",

    #
    # generic science
    #

    "application",
    "applications",
    "challenge",
    "challenges",
    "problem",
    "problems",
    "evaluation",
    "performance",
    "improvement",

    #
    # noisy phrases
    #

    "our approach",
    "our method",
    "proposed method",
    "proposed approach",
    "novel approach",
    "state of the art",
    "experimental results",
    "comparative results",
    "this study",
    "this paper",
    "the authors",
    "the role",
    "the code",
    "our work",
    "the model",
    "the models"
}