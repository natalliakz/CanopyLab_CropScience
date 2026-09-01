# CanopyLab field trial explorer
#
# An R Shiny app that shares its data access and its definition of "yield
# response" with trial-report.qmd, because both call the same package:
# canopytrials. Nothing in this file re-implements a summary.
#
# Publish from Positron with the Publish button, or:
#   rsconnect::deployApp(appFiles = c("app.R", "_brand.yml"))
# Or let .github/workflows/deploy-connect.yml do it on merge to main.

library(shiny)
library(bslib)
library(dplyr)
library(ggplot2)
library(gt)

# canopytrials is a local package not on CRAN; source its R files directly
# so Connect's packrat build phase doesn't need to install it.
local({
  pkg_r <- file.path(getwd(), "canopytrials", "R")
  for (f in c("brand.R", "data-access.R", "summaries.R")) {
    source(file.path(pkg_r, f), local = FALSE)
  }
})

trials <- read_trials()
sites <- read_sites()
colors <- canopylab_colors()

varieties <- sort(unique(trials$variety))
seasons <- sort(unique(trials$season))
regions <- sort(unique(trials$region))

ui <- page_sidebar(
  # One line, and the app wears the same palette and fonts as the Quarto report
  # and the ggplot theme. Change _brand.yml, change all three.
  theme = bs_theme(preset = "shiny"),
  title = "CanopyLab field trial explorer",

  sidebar = sidebar(
    width = 300,
    helpText(
      "Synthetic data for demonstration purposes only.",
      class = "small text-muted"
    ),
    checkboxGroupInput(
      "regions", "Regions",
      choices = regions, selected = regions
    ),
    sliderInput(
      "seasons", "Seasons",
      min = min(seasons), max = max(seasons),
      value = range(seasons), step = 1, sep = ""
    ),
    selectInput(
      "variety", "Highlight a hybrid",
      choices = c("All hybrids" = "", varieties)
    ),
    hr(),
    p(
      "Yield response is always measured against the same hybrid's own untreated",
      "plots — the definition lives in", code("canopytrials::yield_response()"),
      "so this dashboard and the trial report cannot disagree.",
      class = "small text-muted"
    )
  ),

  layout_columns(
    fill = FALSE,
    value_box(
      title = "Plots in view",
      value = textOutput("n_plots"),
      showcase = bsicons::bs_icon("grid-3x3"),
      theme = "primary"
    ),
    value_box(
      title = "Mean yield, protected plots",
      value = textOutput("mean_protected"),
      showcase = bsicons::bs_icon("graph-up"),
      theme = "secondary"
    ),
    value_box(
      title = "Gain over untreated check",
      value = textOutput("mean_gain"),
      showcase = bsicons::bs_icon("plus-slash-minus"),
      theme = "success"
    )
  ),

  layout_columns(
    col_widths = c(7, 5),
    card(
      card_header("Yield response by hybrid"),
      p(
        "Grey is the untreated check; the rule spans the gain.",
        class = "small text-muted mb-1"
      ),
      plotOutput("response_plot", height = "360px")
    ),
    card(
      card_header("Season by season"),
      p(textOutput("season_note", inline = TRUE), class = "small text-muted mb-1"),
      plotOutput("season_plot", height = "360px")
    )
  ),

  card(
    card_header("Station detail"),
    gt_output("site_table")
  ),

  card(
    class = "border-0 bg-transparent",
    p(
      "This project contains synthetic data and analysis created for",
      "demonstration purposes only. All data, insights and business scenarios",
      "were artificially generated using AI.",
      class = "small text-muted mb-0"
    )
  )
)

server <- function(input, output, session) {
  filtered <- reactive({
    req(input$regions)
    trials |>
      filter(
        region %in% input$regions,
        season >= input$seasons[1],
        season <= input$seasons[2]
      )
  })

  response <- reactive({
    df <- filtered()
    validate(need(nrow(df) > 0, "No plots match these filters."))
    yield_response(df)
  })

  output$n_plots <- renderText({
    format(nrow(filtered()), big.mark = ",")
  })

  output$mean_protected <- renderText({
    value <- filtered() |>
      filter(treatment != "Untreated Check") |>
      pull(yield_t_ha) |>
      mean()
    sprintf("%.2f t/ha", value)
  })

  output$mean_gain <- renderText({
    value <- response() |>
      filter(treatment == "Programme Bravo") |>
      pull(gain_vs_check_t_ha) |>
      mean()
    sprintf("+%.2f t/ha", value)
  })

  output$season_note <- renderText({
    if (nzchar(input$variety)) {
      paste0("Solid: all hybrids. Dashed: ", input$variety, ".")
    } else {
      "All hybrids in the selected regions."
    }
  })

  output$response_plot <- renderPlot({
    # The card header does the titling here, so the plot drops its own — at
    # dashboard widths a ggplot title is the first thing to get clipped.
    plot_yield_response(response()) +
      labs(title = NULL, subtitle = NULL, caption = NULL)
  })

  output$season_plot <- renderPlot({
    df <- filtered()
    validate(need(nrow(df) > 0, "No plots match these filters."))

    trend <- df |>
      group_by(season, treatment) |>
      summarise(mean_yield_t_ha = mean(yield_t_ha), .groups = "drop")

    highlight <- if (nzchar(input$variety)) {
      df |>
        filter(variety == input$variety) |>
        group_by(season, treatment) |>
        summarise(mean_yield_t_ha = mean(yield_t_ha), .groups = "drop")
    } else {
      NULL
    }

    plot <- ggplot(trend, aes(season, mean_yield_t_ha, colour = treatment)) +
      geom_line(linewidth = 1) +
      geom_point(size = 2.4) +
      scale_colour_manual(
        values = treatment_colors(),
        # Short labels: at this card width the full programme names clip.
        labels = c("Untreated", "Alpha", "Bravo"),
        breaks = names(treatment_colors())
      ) +
      scale_x_continuous(breaks = sort(unique(trend$season))) +
      labs(x = NULL, y = "Mean yield (t/ha)", colour = NULL) +
      theme_canopylab()

    if (!is.null(highlight)) {
      plot <- plot +
        geom_line(
          data = highlight, linewidth = 0.8, linetype = "31"
        )
    }

    plot
  })

  output$site_table <- render_gt({
    df <- filtered()
    validate(need(nrow(df) > 0, "No plots match these filters."))

    site_summary(df) |>
      gt() |>
      gt::cols_move_to_start(site_name) |>
      fmt_number(mean_yield_t_ha, decimals = 2) |>
      fmt_number(c(mean_disease_index, mean_rainfall_mm), decimals = 1) |>
      cols_label(
        site_name = "Station", region = "Region", plots = "Plots",
        mean_yield_t_ha = "Mean yield (t/ha)",
        mean_disease_index = "Disease index", mean_rainfall_mm = "Rainfall (mm)"
      ) |>
      data_color(
        columns = mean_yield_t_ha,
        palette = c(colors[["mist"]], colors[["leaf"]])
      ) |>
      tab_source_note(md("*Synthetic data, for demonstration purposes only.*")) |>
      tab_options(table.width = pct(100))
  })
}

shinyApp(ui, server)
