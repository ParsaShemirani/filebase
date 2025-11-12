import math

def multiply_lists(l1, l2) -> list[int | float]:
    value_count = len(l1)
    list_of_indexes = range(value_count)

    multiplied_list = []
    for i in list_of_indexes:
        new_value = l1[i] * l2[i]
        multiplied_list.append(new_value)

    return multiplied_list

def dot_product(l1, l2) -> int | float:
    multiplied_list = multiply_lists(l1, l2)

    sum_of_values = 0
    for v in multiplied_list:
        sum_of_values = sum_of_values + v

    return sum_of_values


def norm(l) -> float:
    squared_values_list = []
    for v in l:
        new_value = v * v
        squared_values_list.append(new_value)
    
    sum_of_values = 0
    for v in squared_values_list:
        sum_of_values = sum_of_values + v
    
    square_root_sum_of_values = math.sqrt(sum_of_values)

    return square_root_sum_of_values


def cosine_similarity(l1, l2):
    dp_l1_l2 = dot_product(l1, l2)
    norm_l1 = norm(l1)
    norm_l2 = norm(l2)
    similarity_score = dp_l1_l2 / (norm_l1 * norm_l2)
    
    return similarity_score

def normalize(l: list[int | float]) -> list[float]:
    norm_value = norm(l)

    normalized_l = []
    for v in l:
        new_value = v / norm_value
        normalized_l.append(new_value)

    return normalized_l
