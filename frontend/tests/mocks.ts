export const makeDocxFile = (name = "论文.docx") => new File(["docx"], name, {
  type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
});
