# R port only: the bootstrap draws reproduce numpy's stream (SeedSequence + PCG64 + Generator.choice) and every printed
# number reproduces Python's format(). Fixtures were written by numpy 2.4.6 / Python 3.12 (scratch oracles; the
# pipeline itself never calls Python).

test_that("the numpy SeedSequence / PCG64 / choice stream is reproduced bit for bit", {
  ref <- jsonlite::fromJSON(testthat::test_path("fixtures", "numpy_rng_reference.json"), simplifyVector = FALSE)
  expect_equal(ref$numpy, "2.4.6")
  for (cs in ref$cases) {
    parts <- unlist(cs$parts)
    ent <- sgs_seed_entropy(as.numeric(parts[1]), parts[-1])
    expect_equal(ent, as.numeric(unlist(cs$entropy)), info = paste(parts, collapse = "|"))
    expect_equal(sgs_seedseq_pool(ent), as.numeric(unlist(cs$pool)))
    expect_equal(paste0("0x", sgs_pcg64_raw_hex(ent, 4)), unlist(cs$raw_hex))
    idx <- sgs_numpy_integers6(ent, cs$B * cs$G)
    n <- length(idx)
    expect_equal(idx[1:min(40, n)], as.numeric(unlist(cs$first_idx)))
    expect_equal(idx[(n - min(40, n) + 1):n], as.numeric(unlist(cs$last_idx)))
    expect_equal(tabulate(idx + 1, 6), as.integer(unlist(cs$idx_counts)))
    expect_equal(sum(idx * ((seq_len(n) - 1) %% 1000003)), cs$idx_weighted_sum)
  }
})

test_that("Webb draws: enumeration order is itertools.product (last cluster fastest); random draws fill rows", {
  v <- sgs_webb_draws(3, 9999, NULL)
  expect_true(v$enumerated)
  expect_equal(dim(v$V), c(216, 3))
  expect_equal(v$V[1, ], rep(-sqrt(1.5), 3))
  expect_equal(v$V[2, ], c(-sqrt(1.5), -sqrt(1.5), -1))
  expect_equal(v$V[216, ], rep(sqrt(1.5), 3))
  r <- sgs_webb_draws(7, 3, sgs_seed_entropy(20260925, "C1", "growth_previous_year_pct"))
  expect_false(r$enumerated)
  idx <- c(5, 3, 2, 2, 5, 2, 5, 0, 2, 1, 4, 1, 1, 0, 3, 3, 4, 2, 3, 1, 4)  # numpy rng.choice(WEBB, size=(3, 7)) indices
  expect_equal(r$V, matrix(SGS_WEBB[idx + 1], 3, 7, byrow = TRUE))
})

test_that("zlib CRC-32 of UTF-8 text", {
  expect_equal(sgs_crc32("C1"), 3411217923)
  expect_equal(sgs_crc32("growth_previous_year_pct"), 3087014168)
  expect_equal(sgs_crc32(""), 0)
  expect_equal(sgs_crc32("The quick brown fox jumps over the lazy dog"), 1095738169)  # 0x414FA339
})

test_that("Python-exact number formatting (f / ,f / g / repr and report.fmt)", {
  ref <- jsonlite::fromJSON(testthat::test_path("fixtures", "python_format_reference.json"))
  x <- as.numeric(ref$hex)
  expect_false(anyNA(x))
  expect_equal(vapply(x, sgs_py_fixed, "", d = 4), ref$f4)
  expect_equal(vapply(x, sgs_py_fixed, "", d = 4, comma = TRUE), ref$cf4)
  expect_equal(vapply(x, sgs_py_fixed, "", d = 3), ref$f3)
  expect_equal(vapply(x, sgs_py_g, "", p = 4), ref$g4)
  expect_equal(vapply(x, sgs_py_g, "", p = 6), ref$g6)
  expect_equal(vapply(x, sgs_py_repr_float, ""), ref$repr)
  expect_equal(vapply(x, sgs_fmt, ""), ref$fmt)
  expect_equal(sgs_fmt(NA), "n/a")
  expect_equal(sgs_fmt(-Inf), "-inf")
  expect_equal(sgs_ci_text(-Inf, Inf), "[-inf, +inf]")
  expect_equal(sgs_py_fixed(0.00005, 4), "0.0001")  # sprintf("%.4f") gives 0.0000 on this machine
})
