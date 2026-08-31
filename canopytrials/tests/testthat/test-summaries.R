# Tests run against a small fixture rather than the generated CSVs, so `R CMD
# check` passes on a fresh clone where the synthetic data has not been built yet.
# This is the whole argument for putting shared logic in a package: it can be
# tested without the rest of the project being present.

fixture <- function() {
  data.frame(
    variety = rep(c("CL-Test 01", "CL-Test 02"), each = 4),
    treatment = rep(c("Untreated Check", "Untreated Check", "Programme Bravo", "Programme Bravo"), 2),
    yield_t_ha = c(8, 9, 10, 11, 6, 7, 9, 10),
    disease_pressure_index = c(60, 50, 10, 12, 70, 66, 14, 10),
    season = 2025L,
    region = "Test Region",
    site_name = "Test Station",
    rainfall_mm = 500,
    stringsAsFactors = FALSE
  )
}

test_that("yield_response measures the gain against the same hybrid's own check", {
  response <- yield_response(fixture())

  expect_s3_class(response, "data.frame")
  expect_setequal(
    names(response),
    c(
      "variety", "treatment", "plots", "mean_yield_t_ha", "sd_yield_t_ha",
      "mean_disease_index", "gain_vs_check_t_ha"
    )
  )

  # CL-Test 01: check mean 8.5, treated mean 10.5 -> gain 2.0
  gain <- response$gain_vs_check_t_ha[
    response$variety == "CL-Test 01" & response$treatment == "Programme Bravo"
  ]
  expect_equal(gain, 2)

  # CL-Test 02 has lower potential but the same 2.5 t/ha response. A gain
  # measured against the trial-wide average would report these as different.
  gain_two <- response$gain_vs_check_t_ha[
    response$variety == "CL-Test 02" & response$treatment == "Programme Bravo"
  ]
  expect_equal(gain_two, 3)

  # The control's gain over itself is zero, by construction.
  expect_true(all(
    response$gain_vs_check_t_ha[response$treatment == "Untreated Check"] == 0
  ))
})

test_that("yield_response refuses to guess when there is no control", {
  no_check <- fixture()[fixture()$treatment != "Untreated Check", ]
  expect_error(yield_response(no_check), "Untreated Check")
})

test_that("site_summary returns one row per station, best first", {
  summary <- site_summary(fixture())
  expect_equal(nrow(summary), 1)
  expect_equal(summary$plots, 8)
  expect_equal(summary$mean_yield_t_ha, mean(fixture()$yield_t_ha))
})

test_that("season_trend filters to one programme", {
  trend <- season_trend(fixture(), treatment = "Programme Bravo")
  expect_equal(nrow(trend), 2)
  expect_equal(sort(trend$mean_yield_t_ha), c(9.5, 10.5))
})

test_that("the brand palette is complete and fixed", {
  expect_named(
    treatment_colors(),
    c("Untreated Check", "Programme Alpha", "Programme Bravo")
  )
  expect_true(all(grepl("^#[0-9A-Fa-f]{6}$", canopylab_colors())))
})

test_that("plot_yield_response returns a ggplot", {
  expect_s3_class(plot_yield_response(yield_response(fixture())), "ggplot")
})

test_that("trial_data_path says how to fix a missing file", {
  expect_error(
    trial_data_path("no-such-file.csv", root = tempdir()),
    "generate_data.py"
  )
})
