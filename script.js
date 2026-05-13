let extractedTransactions = [];

async function processPDF() {

  const fileInput =
    document.getElementById('pdfUpload');

  if (!fileInput.files.length) {
    alert("Please upload a PDF");
    return;
  }

  const file = fileInput.files[0];

  const status =
    document.getElementById('status');

  status.innerHTML = "Loading PDF...";

  const arrayBuffer =
    await file.arrayBuffer();

  const pdf =
    await pdfjsLib.getDocument({
      data: arrayBuffer
    }).promise;

  let fullText = "";

  for (
    let pageNum = 1;
    pageNum <= pdf.numPages;
    pageNum++
  ) {

    status.innerHTML =
      `Processing page ${pageNum} of ${pdf.numPages}...`;

    const page =
      await pdf.getPage(pageNum);

    const viewport =
      page.getViewport({
        scale: 2
      });

    const canvas =
      document.createElement('canvas');

    const context =
      canvas.getContext('2d');

    canvas.height =
      viewport.height;

    canvas.width =
      viewport.width;

    await page.render({
      canvasContext: context,
      viewport: viewport
    }).promise;

    const result =
      await Tesseract.recognize(
        canvas,
        'eng'
      );

    fullText +=
      result.data.text + "\n";
  }

  console.log(fullText);

  status.innerHTML =
    "Extracting transactions...";

  extractTransactions(fullText);

  status.innerHTML =
    `Done. Found ${extractedTransactions.length} transactions.`;
}

function extractTransactions(text) {

  extractedTransactions = [];

  const lines =
    text.split('\n');

  const tbody =
    document.querySelector(
      '#resultsTable tbody'
    );

  tbody.innerHTML = "";

  lines.forEach(line => {

    line = line.trim();

    if (!line) return;

    const dateMatch =
      line.match(
        /(\d{2}[\/\-]\d{2}[\/\-]\d{2,4})|(\d{1,2}\s[A-Za-z]{3})/
      );

    const amountMatch =
      line.match(
        /-?\d{1,3}(,\d{3})*(\.\d{2})/
      );

    if (dateMatch && amountMatch) {

      const date =
        dateMatch[0];

      const amount =
        amountMatch[0]
          .replace(/,/g, '');

      let description =
        line
          .replace(date, '')
          .replace(amountMatch[0], '')
          .trim();

      if (
        description.length < 2
      ) return;

      const transaction = {
        date,
        description,
        amount
      };

      extractedTransactions.push(
        transaction
      );

      const row =
        document.createElement('tr');

      row.innerHTML = `
        <td>${date}</td>
        <td>${description}</td>
        <td>${amount}</td>
      `;

      tbody.appendChild(row);
    }
  });
}

function downloadCSV() {

  if (!extractedTransactions.length) {
    alert("No transactions found");
    return;
  }

  let csv =
    "Date,Description,Amount\n";

  extractedTransactions.forEach(t => {

    csv +=
      `${t.date},"${t.description}",${t.amount}\n`;
  });

  const blob =
    new Blob(
      [csv],
      { type: 'text/csv' }
    );

  const link =
    document.createElement('a');

  link.href =
    URL.createObjectURL(blob);

  link.download =
    "transactions.csv";

  link.click();
}
