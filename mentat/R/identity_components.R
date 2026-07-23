assign_identity_components <- function(group) {
  group <- data.table::copy(group)
  count <- nrow(group)
  if (!count) {
    group[, identity_component := integer()]
    return(group)
  }

  parent <- seq_len(count)
  root <- function(index) {
    while (parent[index] != index) {
      parent[index] <<- parent[parent[index]]
      index <- parent[index]
    }
    index
  }
  unite <- function(left, right) {
    left_root <- root(left)
    right_root <- root(right)
    if (left_root != right_root) {
      lower <- min(left_root, right_root)
      upper <- max(left_root, right_root)
      parent[upper] <<- lower
    }
  }
  unite_key_groups <- function(keys) {
    valid_indices <- which(nzchar(keys))
    if (length(valid_indices) < 2L) {
      return(invisible(NULL))
    }
    for (indices in split(valid_indices, keys[valid_indices])) {
      if (length(indices) < 2L) {
        next
      }
      anchor <- min(indices)
      for (index in indices[indices != anchor]) {
        unite(anchor, index)
      }
    }
    invisible(NULL)
  }

  if (any(group$known_executive) || any(group$verified_employee)) {
    if (count > 1L) {
      for (index in 2L:count) {
        unite(1L, index)
      }
    }
  } else if (count > 1L) {
    zip5 <- ifelse(
      nzchar(group$zipcode),
      substr(group$zipcode, 1L, 5L),
      ""
    )
    location <- ifelse(
      nzchar(group$city) & nzchar(group$state),
      paste(group$city, group$state, sep = "|"),
      ""
    )
    exact_occupation <- ifelse(
      nzchar(group$exact_name_key) & nzchar(group$occupation_key),
      paste(group$exact_name_key, group$occupation_key, sep = "|"),
      ""
    )
    occupation_employer <- ifelse(
      nzchar(group$occupation_key) & nzchar(group$employer_key),
      paste(group$occupation_key, group$employer_key, sep = "|"),
      ""
    )

    # Each index represents one disjunct in the original pairwise predicate.
    # For occupation+employer, same-exact-name pairs are harmless extra edges:
    # exact-name+occupation already connects them. Uniting the complete key
    # group therefore preserves the original connected components, including
    # the original rule that two blank exact-name keys may still merge.
    unite_key_groups(zip5)
    unite_key_groups(location)
    unite_key_groups(exact_occupation)
    unite_key_groups(occupation_employer)
  }

  roots <- vapply(seq_len(count), root, integer(1L))
  root_order <- unique(roots[order(
    group$exact_name_key,
    group$state,
    group$zipcode,
    group$sub_id
  )])
  group[, identity_component := match(roots, root_order)]
  group
}
