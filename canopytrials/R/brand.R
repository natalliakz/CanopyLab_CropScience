#' CanopyLab chart colours
#'
#' The same hex values as `_brand.yml`, carried in the package so that a chart
#' drawn by a script, a report or an app comes out the same colour. `_brand.yml`
#' themes the HTML around the chart; this themes the chart itself.
#'
#' @return A named character vector of hex colours.
#' @export
#'
#' @examples
#' canopylab_colors()[["leaf"]]
canopylab_colors <- function() {
  c(
    leaf = "#3E7B52",
    canopy = "#2A5638",
    sprout = "#8FBF7A",
    loam = "#8A6A4A",
    grain = "#D8A93B",
    sky = "#3D7CA8",
    clay = "#B4472E",
    stone = "#6E7671",
    mist = "#EFF3EE",
    hairline = "#D6DED7",
    ink = "#1A1F1B"
  )
}

#' Colours for the three protection programmes
#'
#' Fixed, so a programme keeps its colour when a filter drops one of the others.
#' The untreated check is deliberately the neutral stone: it is the baseline, not
#' a competitor.
#'
#' @return A named character vector, one colour per programme.
#' @export
treatment_colors <- function() {
  colors <- canopylab_colors()
  c(
    "Untreated Check" = colors[["stone"]],
    "Programme Alpha" = colors[["sky"]],
    "Programme Bravo" = colors[["leaf"]]
  )
}

#' A recessive ggplot2 theme for CanopyLab charts
#'
#' Grid and axes are faint on purpose: the data marks should be the only
#' assertive thing on the panel.
#'
#' @param base_size Base font size in points.
#'
#' @return A ggplot2 theme object.
#' @export
theme_canopylab <- function(base_size = 12) {
  colors <- canopylab_colors()
  ggplot2::theme_minimal(base_size = base_size) +
    ggplot2::theme(
      plot.title = ggplot2::element_text(
        face = "bold", colour = colors[["canopy"]], size = ggplot2::rel(1.15)
      ),
      plot.subtitle = ggplot2::element_text(colour = colors[["stone"]]),
      plot.caption = ggplot2::element_text(colour = colors[["stone"]], size = ggplot2::rel(0.8)),
      plot.title.position = "plot",
      axis.title = ggplot2::element_text(colour = colors[["stone"]]),
      axis.text = ggplot2::element_text(colour = colors[["stone"]]),
      panel.grid.minor = ggplot2::element_blank(),
      panel.grid.major = ggplot2::element_line(colour = colors[["hairline"]], linewidth = 0.3),
      strip.text = ggplot2::element_text(face = "bold", colour = colors[["canopy"]]),
      legend.position = "top",
      legend.title = ggplot2::element_blank()
    )
}

#' Plot the yield response to each protection programme
#'
#' A dot per hybrid and programme rather than a bar chart: bars with a fill
#' aesthetic invite stacking, and stacked means add up to a number that does not
#' exist. Three dots on a row show the ranking and the size of each gap.
#'
#' @param response Output of [yield_response()].
#'
#' @return A ggplot object.
#' @export
plot_yield_response <- function(response) {
  colors <- canopylab_colors()

  ggplot2::ggplot(
    response,
    ggplot2::aes(
      x = .data$mean_yield_t_ha,
      y = stats::reorder(.data$variety, .data$mean_yield_t_ha),
      colour = .data$treatment
    )
  ) +
    ggplot2::geom_line(
      ggplot2::aes(group = .data$variety),
      colour = colors[["hairline"]],
      linewidth = 1.5
    ) +
    ggplot2::geom_point(size = 3.4) +
    ggplot2::scale_colour_manual(values = treatment_colors()) +
    ggplot2::labs(
      title = "Every hybrid gains from a protection programme, by different amounts",
      subtitle = "Mean yield across all stations and seasons; the grey rule spans the gap",
      x = "Mean yield (t/ha)",
      y = NULL,
      caption = "Synthetic data, generated for demonstration purposes only."
    ) +
    theme_canopylab()
}
