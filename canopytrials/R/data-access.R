#' Locate the synthetic trial data
#'
#' The data is generated rather than checked into version control, so every entry
#' point has to be able to find it and to say something useful when it is missing.
#'
#' @param file Name of the file inside the project's `data/` directory.
#' @param root Project root. Defaults to the `CANOPYLAB_DATA_ROOT` environment
#'   variable if it is set, then to the working directory, then to its parent --
#'   which is what makes the same call work from the project root, from a
#'   `notebooks/` subdirectory, and from a deployed bundle on Posit Connect.
#'
#' @return A path to an existing file.
#' @export
#'
#' @examples
#' \dontrun{
#' trial_data_path("synthetic-field-trials.csv")
#' }
trial_data_path <- function(file = "synthetic-field-trials.csv", root = NULL) {
  candidates <- if (!is.null(root)) {
    root
  } else {
    c(Sys.getenv("CANOPYLAB_DATA_ROOT", unset = NA), ".", "..", "../..")
  }
  candidates <- candidates[!is.na(candidates)]

  for (candidate in candidates) {
    path <- file.path(candidate, "data", file)
    if (file.exists(path)) {
      return(normalizePath(path))
    }
  }

  stop(
    "Could not find data/", file, ".\n",
    "Generate it first:  uv run python data/generate_data.py",
    call. = FALSE
  )
}

#' Read the synthetic field trial results
#'
#' One row per harvested plot.
#'
#' @inheritParams trial_data_path
#'
#' @return A tibble of trial plots.
#' @export
read_trials <- function(root = NULL) {
  readr::read_csv(
    trial_data_path("synthetic-field-trials.csv", root = root),
    show_col_types = FALSE
  )
}

#' Read the trial station metadata
#'
#' @inheritParams trial_data_path
#'
#' @return A tibble of trial stations.
#' @export
read_sites <- function(root = NULL) {
  readr::read_csv(
    trial_data_path("synthetic-sites.csv", root = root),
    show_col_types = FALSE
  )
}

#' Connect to the trial DuckDB database
#'
#' The same file that Positron's Connections pane browses and that the `.ggsql`
#' queries chart. Remember to `DBI::dbDisconnect()` when you are done; in a Shiny
#' app that belongs in `shiny::onStop()`.
#'
#' @inheritParams trial_data_path
#' @param read_only Open the database read-only. `TRUE` by default, because
#'   reports and apps have no business writing to it.
#'
#' @return A DBI connection.
#' @export
connect_trials_db <- function(root = NULL, read_only = TRUE) {
  DBI::dbConnect(
    duckdb::duckdb(),
    dbdir = trial_data_path("synthetic-agronomy.duckdb", root = root),
    read_only = read_only
  )
}
