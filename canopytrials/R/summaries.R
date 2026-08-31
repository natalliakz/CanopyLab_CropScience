#' Yield response to each protection programme
#'
#' The number every trial report opens with: mean yield per hybrid and programme,
#' and the gain over the untreated check. Defining it once, here, is why the
#' report, the dashboard and the API cannot quietly disagree about it.
#'
#' @param trials Trial plots, as returned by [read_trials()].
#' @param check Name of the untreated control programme.
#'
#' @return A tibble with one row per hybrid and programme: `variety`,
#'   `treatment`, `plots`, `mean_yield_t_ha`, `sd_yield_t_ha`,
#'   `mean_disease_index` and `gain_vs_check_t_ha`.
#' @export
yield_response <- function(trials, check = "Untreated Check") {
  stopifnot(is.data.frame(trials))
  if (!check %in% trials$treatment) {
    stop("No plots found for the control programme '", check, "'.", call. = FALSE)
  }

  summary <- trials |>
    dplyr::group_by(.data$variety, .data$treatment) |>
    dplyr::summarise(
      plots = dplyr::n(),
      mean_yield_t_ha = mean(.data$yield_t_ha),
      sd_yield_t_ha = stats::sd(.data$yield_t_ha),
      mean_disease_index = mean(.data$disease_pressure_index),
      .groups = "drop"
    )

  # The gain is measured against the same hybrid's own untreated plots, never
  # against the trial-wide average: hybrids differ in potential, and comparing
  # across them would credit the programme with genetics.
  checks <- summary |>
    dplyr::filter(.data$treatment == check) |>
    dplyr::select("variety", check_yield = "mean_yield_t_ha")

  summary |>
    dplyr::left_join(checks, by = "variety") |>
    dplyr::mutate(gain_vs_check_t_ha = .data$mean_yield_t_ha - .data$check_yield) |>
    dplyr::select(-"check_yield") |>
    dplyr::arrange(.data$variety, .data$treatment)
}

#' Summarise trial results by station
#'
#' @param trials Trial plots, as returned by [read_trials()].
#'
#' @return A tibble with one row per station, ordered by mean yield.
#' @export
site_summary <- function(trials) {
  trials |>
    dplyr::group_by(.data$region, .data$site_name) |>
    dplyr::summarise(
      plots = dplyr::n(),
      mean_yield_t_ha = mean(.data$yield_t_ha),
      mean_disease_index = mean(.data$disease_pressure_index),
      mean_rainfall_mm = mean(.data$rainfall_mm),
      .groups = "drop"
    ) |>
    dplyr::arrange(dplyr::desc(.data$mean_yield_t_ha))
}

#' Season-by-season yield for one protection programme
#'
#' @param trials Trial plots, as returned by [read_trials()].
#' @param treatment Programme to report on.
#'
#' @return A tibble with one row per season and hybrid.
#' @export
season_trend <- function(trials, treatment = "Programme Bravo") {
  trials |>
    dplyr::filter(.data$treatment == .env$treatment) |>
    dplyr::group_by(.data$season, .data$variety) |>
    dplyr::summarise(
      mean_yield_t_ha = mean(.data$yield_t_ha),
      mean_rainfall_mm = mean(.data$rainfall_mm),
      .groups = "drop"
    )
}
