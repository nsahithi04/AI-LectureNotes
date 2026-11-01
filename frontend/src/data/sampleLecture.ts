import type { Lecture } from "@/types/lecture"

/** Example of a completed lecture, in exactly the shape GET /api/lectures/{id} returns. */
export const sampleLecture: Lecture = {
  id: "sample",
  title: "Introduction to Machine Learning",
  input_type: "video",
  status: "completed",
  note_types: ["detailed", "short", "important"],
  source: { filename: "machine-learning-lecture.mp4", file_size: 124_100_000, characters: null },
  error: null,
  created_at: "2026-10-29T10:42:00Z",
  notes: {
    detailed: [
      { type: "heading", level: 1, text: "What is machine learning?" },
      {
        type: "paragraph",
        text: "Welcome to our first lecture on machine learning. Rather than programming every decision, we show a system enough meaningful examples so it can learn patterns from data and make decisions with minimal human intervention.",
      },
      {
        type: "paragraph",
        text: "A model is a mathematical representation learned from training data. It uses the patterns in that data to make predictions about new, unseen examples, so the quality of the examples directly shapes the quality of the model.",
      },
      { type: "heading", level: 1, text: "Main learning paradigms" },
      { type: "heading", level: 2, text: "Supervised learning" },
      {
        type: "paragraph",
        text: "In supervised learning the examples come with labels: each input is paired with the correct output. Think of an inbox where messages have already been marked as spam or not spam. Labels can come from people, existing systems or observed outcomes; what matters is that they are a reliable target.",
      },
      {
        type: "bullets",
        items: [
          "Classification predicts a category, such as whether an email is spam.",
          "Regression predicts a continuous value, such as a house price.",
        ],
      },
      { type: "heading", level: 2, text: "Unsupervised learning" },
      {
        type: "paragraph",
        text: "Unsupervised learning explores unlabeled data to discover hidden structure. A music service, for example, can cluster listeners with similar habits without knowing those groups in advance.",
      },
      { type: "heading", level: 1, text: "Training and evaluation" },
      {
        type: "paragraph",
        text: "Data is divided into a training set and a test set. The model learns from the training set, and the test set measures how well it generalizes. A model that memorizes its training data but performs poorly on new data is overfitting.",
      },
    ],
    short: [
      { type: "heading", level: 1, text: "Machine learning" },
      {
        type: "bullets",
        items: [
          "Systems learn patterns from examples instead of fixed rules.",
          "A model is a mathematical representation learned from training data.",
        ],
      },
      { type: "heading", level: 1, text: "Learning paradigms" },
      {
        type: "bullets",
        items: [
          "Supervised: labeled data; classification (categories) and regression (values).",
          "Unsupervised: unlabeled data; finds structure, e.g. clustering.",
        ],
      },
      { type: "heading", level: 1, text: "Evaluation" },
      {
        type: "bullets",
        items: ["Train on one set, test on unseen data.", "Overfitting = memorizing training data, failing on new data."],
      },
    ],
    important: [
      {
        type: "bullets",
        items: [
          "Machine learning learns patterns from data rather than following explicit rules.",
          "Supervised learning uses labels; unsupervised learning discovers structure.",
          "Always evaluate on data the model hasn't seen.",
          "Overfitting means the model doesn't generalize.",
        ],
      },
    ],
  },
}
