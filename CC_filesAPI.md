# PDF support

> Process PDFs with Claude. Extract text, analyze charts, and understand visual content from your documents.

You can now ask Claude about any text, pictures, charts, and tables in PDFs you provide. Some sample use cases:

- Analyzing financial reports and understanding charts/tables
- Extracting key information from legal documents
- Translation assistance for documents
- Converting document information into structured formats

## Before you begin

### Check PDF requirements

Claude works with any standard PDF. However, you should ensure your request size meets these requirements when using PDF support:

| Requirement               | Limit                                  |
| ------------------------- | -------------------------------------- |
| Maximum request size      | 32MB                                   |
| Maximum pages per request | 100                                    |
| Format                    | Standard PDF (no passwords/encryption) |

Please note that both limits are on the entire request payload, including any other content sent alongside PDFs.

Since PDF support relies on Claude's vision capabilities, it is subject to the same [limitations and considerations](/en/docs/build-with-claude/vision#limitations) as other vision tasks.

### Supported platforms and models

PDF support is currently supported via direct API access and Google Vertex AI on:

- Claude Opus 4 (`claude-opus-4-20250514`)
- Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- Claude Sonnet 3.7 (`claude-3-7-sonnet-20250219`)
- Claude Sonnet 3.5 models (`claude-3-5-sonnet-20241022`, `claude-3-5-sonnet-20240620`)
- Claude Haiku 3.5 (`claude-3-5-haiku-20241022`)

PDF support is now available on Amazon Bedrock with the following considerations:

### Amazon Bedrock PDF Support

When using PDF support through Amazon Bedrock's Converse API, there are two distinct document processing modes:

<Note>
  **Important**: To access Claude's full visual PDF understanding capabilities in the Converse API, you must enable citations. Without citations enabled, the API falls back to basic text extraction only. Learn more about [working with citations](/en/docs/build-with-claude/citations).
</Note>

#### Document Processing Modes

1. **Converse Document Chat** (Original mode - Text extraction only)

   - Provides basic text extraction from PDFs
   - Cannot analyze images, charts, or visual layouts within PDFs
   - Uses approximately 1,000 tokens for a 3-page PDF
   - Automatically used when citations are not enabled

2. **Claude PDF Chat** (New mode - Full visual understanding)
   - Provides complete visual analysis of PDFs
   - Can understand and analyze charts, graphs, images, and visual layouts
   - Processes each page as both text and image for comprehensive understanding
   - Uses approximately 7,000 tokens for a 3-page PDF
   - **Requires citations to be enabled** in the Converse API

#### Key Limitations

- **Converse API**: Visual PDF analysis requires citations to be enabled. There is currently no option to use visual analysis without citations (unlike the InvokeModel API).
- **InvokeModel API**: Provides full control over PDF processing without forced citations.

#### Common Issues

If customers report that Claude isn't seeing images or charts in their PDFs when using the Converse API, they likely need to enable the citations flag. Without it, Converse falls back to basic text extraction only.

<Note>
  This is a known constraint with the Converse API that we're working to address. For applications that require visual PDF analysis without citations, consider using the InvokeModel API instead.
</Note>

<Note>
  For non-PDF files like .csv, .xlsx, .docx, .md, or .txt files, see [Working with other file formats](/en/docs/build-with-claude/files#working-with-other-file-formats).
</Note>

---

## Process PDFs with Claude

### Send your first PDF request

Let's start with a simple example using the Messages API. You can provide PDFs to Claude in three ways:

1. As a URL reference to a PDF hosted online
2. As a base64-encoded PDF in `document` content blocks
3. By a `file_id` from the [Files API](/en/docs/build-with-claude/files)

#### Option 1: URL-based PDF document

The simplest approach is to reference a PDF directly from a URL:

<CodeGroup>
  ```bash Shell
   curl https://api.anthropic.com/v1/messages \
     -H "content-type: application/json" \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -d '{
       "model": "claude-opus-4-20250514",
       "max_tokens": 1024,
       "messages": [{
           "role": "user",
           "content": [{
               "type": "document",
               "source": {
                   "type": "url",
                   "url": "https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf"
               }
           },
           {
               "type": "text",
               "text": "What are the key findings in this document?"
           }]
       }]
   }'
  ```

```Python Python
import anthropic

client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-opus-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "url",
                        "url": "https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf"
                    }
                },
                {
                    "type": "text",
                    "text": "What are the key findings in this document?"
                }
            ]
        }
    ],
)

print(message.content)
```

```TypeScript TypeScript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic();

async function main() {
  const response = await anthropic.messages.create({
    model: 'claude-opus-4-20250514',
    max_tokens: 1024,
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'document',
            source: {
              type: 'url',
              url: 'https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf',
            },
          },
          {
            type: 'text',
            text: 'What are the key findings in this document?',
          },
        ],
      },
    ],
  });

  console.log(response);
}

main();
```

```java Java
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.*;

public class PdfExample {
    public static void main(String[] args) {
        AnthropicClient client = AnthropicOkHttpClient.fromEnv();

        // Create document block with URL
        DocumentBlockParam documentParam = DocumentBlockParam.builder()
                .urlPdfSource("https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf")
                .build();

        // Create a message with document and text content blocks
        MessageCreateParams params = MessageCreateParams.builder()
                .model(Model.CLAUDE_OPUS_4_20250514)
                .maxTokens(1024)
                .addUserMessageOfBlockParams(
                        List.of(
                                ContentBlockParam.ofDocument(documentParam),
                                ContentBlockParam.ofText(
                                        TextBlockParam.builder()
                                                .text("What are the key findings in this document?")
                                                .build()
                                )
                        )
                )
                .build();

        Message message = client.messages().create(params);
        System.out.println(message.content());
    }
}
```

</CodeGroup>

#### Option 2: Base64-encoded PDF document

If you need to send PDFs from your local system or when a URL isn't available:

<CodeGroup>
  ```bash Shell
  # Method 1: Fetch and encode a remote PDF
  curl -s "https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf" | base64 | tr -d '\n' > pdf_base64.txt

# Method 2: Encode a local PDF file

# base64 document.pdf | tr -d '\n' > pdf_base64.txt

# Create a JSON request file using the pdf_base64.txt content

jq -n --rawfile PDF_BASE64 pdf_base64.txt '{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"messages": [{
"role": "user",
"content": [{
"type": "document",
"source": {
"type": "base64",
"media_type": "application/pdf",
"data": $PDF_BASE64
}
},
{
"type": "text",
"text": "What are the key findings in this document?"
}]
}]
}' > request.json

# Send the API request using the JSON file

curl https://api.anthropic.com/v1/messages \
 -H "content-type: application/json" \
 -H "x-api-key: $ANTHROPIC_API_KEY" \
 -H "anthropic-version: 2023-06-01" \
 -d @request.json

````

```Python Python
import anthropic
import base64
import httpx

# First, load and encode the PDF
pdf_url = "https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf"
pdf_data = base64.standard_b64encode(httpx.get(pdf_url).content).decode("utf-8")

# Alternative: Load from a local file
# with open("document.pdf", "rb") as f:
#     pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

# Send to Claude using base64 encoding
client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-opus-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data
                    }
                },
                {
                    "type": "text",
                    "text": "What are the key findings in this document?"
                }
            ]
        }
    ],
)

print(message.content)
````

```TypeScript TypeScript
import Anthropic from '@anthropic-ai/sdk';
import fetch from 'node-fetch';
import fs from 'fs';

async function main() {
  // Method 1: Fetch and encode a remote PDF
  const pdfURL = "https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf";
  const pdfResponse = await fetch(pdfURL);
  const arrayBuffer = await pdfResponse.arrayBuffer();
  const pdfBase64 = Buffer.from(arrayBuffer).toString('base64');

  // Method 2: Load from a local file
  // const pdfBase64 = fs.readFileSync('document.pdf').toString('base64');

  // Send the API request with base64-encoded PDF
  const anthropic = new Anthropic();
  const response = await anthropic.messages.create({
    model: 'claude-opus-4-20250514',
    max_tokens: 1024,
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'document',
            source: {
              type: 'base64',
              media_type: 'application/pdf',
              data: pdfBase64,
            },
          },
          {
            type: 'text',
            text: 'What are the key findings in this document?',
          },
        ],
      },
    ],
  });

  console.log(response);
}

main();
```

```java Java
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Base64;
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.ContentBlockParam;
import com.anthropic.models.messages.DocumentBlockParam;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.TextBlockParam;

public class PdfExample {
    public static void main(String[] args) throws IOException, InterruptedException {
        AnthropicClient client = AnthropicOkHttpClient.fromEnv();

        // Method 1: Download and encode a remote PDF
        String pdfUrl = "https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf";
        HttpClient httpClient = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(pdfUrl))
                .GET()
                .build();

        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        String pdfBase64 = Base64.getEncoder().encodeToString(response.body());

        // Method 2: Load from a local file
        // byte[] fileBytes = Files.readAllBytes(Path.of("document.pdf"));
        // String pdfBase64 = Base64.getEncoder().encodeToString(fileBytes);

        // Create document block with base64 data
        DocumentBlockParam documentParam = DocumentBlockParam.builder()
                .base64PdfSource(pdfBase64)
                .build();

        // Create a message with document and text content blocks
        MessageCreateParams params = MessageCreateParams.builder()
                .model(Model.CLAUDE_OPUS_4_20250514)
                .maxTokens(1024)
                .addUserMessageOfBlockParams(
                        List.of(
                                ContentBlockParam.ofDocument(documentParam),
                                ContentBlockParam.ofText(TextBlockParam.builder().text("What are the key findings in this document?").build())
                        )
                )
                .build();

        Message message = client.messages().create(params);
        message.content().stream()
                .flatMap(contentBlock -> contentBlock.text().stream())
                .forEach(textBlock -> System.out.println(textBlock.text()));
    }
}
```

</CodeGroup>

#### Option 3: Files API

For PDFs you'll use repeatedly, or when you want to avoid encoding overhead, use the [Files API](/en/docs/build-with-claude/files):

<CodeGroup>
  ```bash Shell
  # First, upload your PDF to the Files API
  curl -X POST https://api.anthropic.com/v1/files \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: files-api-2025-04-14" \
    -F "file=@document.pdf"

# Then use the returned file_id in your message

curl https://api.anthropic.com/v1/messages \
 -H "content-type: application/json" \
 -H "x-api-key: $ANTHROPIC_API_KEY" \
 -H "anthropic-version: 2023-06-01" \
 -H "anthropic-beta: files-api-2025-04-14" \
 -d '{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"messages": [{
"role": "user",
"content": [{
"type": "document",
"source": {
"type": "file",
"file_id": "file_abc123"
}
},
{
"type": "text",
"text": "What are the key findings in this document?"
}]
}]
}'

````

```python Python
import anthropic

client = anthropic.Anthropic()

# Upload the PDF file
with open("document.pdf", "rb") as f:
    file_upload = client.beta.files.upload(file=("document.pdf", f, "application/pdf"))

# Use the uploaded file in a message
message = client.beta.messages.create(
    model="claude-opus-4-20250514",
    max_tokens=1024,
    betas=["files-api-2025-04-14"],
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "file",
                        "file_id": file_upload.id
                    }
                },
                {
                    "type": "text",
                    "text": "What are the key findings in this document?"
                }
            ]
        }
    ],
)

print(message.content)
````

```typescript TypeScript
import { Anthropic, toFile } from "@anthropic-ai/sdk";
import fs from "fs";

const anthropic = new Anthropic();

async function main() {
  // Upload the PDF file
  const fileUpload = await anthropic.beta.files.upload(
    {
      file: toFile(fs.createReadStream("document.pdf"), undefined, {
        type: "application/pdf",
      }),
    },
    {
      betas: ["files-api-2025-04-14"],
    }
  );

  // Use the uploaded file in a message
  const response = await anthropic.beta.messages.create({
    model: "claude-opus-4-20250514",
    max_tokens: 1024,
    betas: ["files-api-2025-04-14"],
    messages: [
      {
        role: "user",
        content: [
          {
            type: "document",
            source: {
              type: "file",
              file_id: fileUpload.id,
            },
          },
          {
            type: "text",
            text: "What are the key findings in this document?",
          },
        ],
      },
    ],
  });

  console.log(response);
}

main();
```

```java Java
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.File;
import com.anthropic.models.files.FileUploadParams;
import com.anthropic.models.messages.*;

public class PdfFilesExample {
    public static void main(String[] args) throws IOException {
        AnthropicClient client = AnthropicOkHttpClient.fromEnv();

        // Upload the PDF file
        File file = client.beta().files().upload(FileUploadParams.builder()
                .file(Files.newInputStream(Path.of("document.pdf")))
                .build());

        // Use the uploaded file in a message
        DocumentBlockParam documentParam = DocumentBlockParam.builder()
                .fileSource(file.id())
                .build();

        MessageCreateParams params = MessageCreateParams.builder()
                .model(Model.CLAUDE_OPUS_4_20250514)
                .maxTokens(1024)
                .addUserMessageOfBlockParams(
                        List.of(
                                ContentBlockParam.ofDocument(documentParam),
                                ContentBlockParam.ofText(
                                        TextBlockParam.builder()
                                                .text("What are the key findings in this document?")
                                                .build()
                                )
                        )
                )
                .build();

        Message message = client.messages().create(params);
        System.out.println(message.content());
    }
}
```

</CodeGroup>

### How PDF support works

When you send a PDF to Claude, the following steps occur:

<Steps>
  <Step title="The system extracts the contents of the document.">
    * The system converts each page of the document into an image.
    * The text from each page is extracted and provided alongside each page's image.
  </Step>

  <Step title="Claude analyzes both the text and images to better understand the document.">
    * Documents are provided as a combination of text and images for analysis.
    * This allows users to ask for insights on visual elements of a PDF, such as charts, diagrams, and other non-textual content.
  </Step>

  <Step title="Claude responds, referencing the PDF's contents if relevant.">
    Claude can reference both textual and visual content when it responds. You can further improve performance by integrating PDF support with:

    * **Prompt caching**: To improve performance for repeated analysis.
    * **Batch processing**: For high-volume document processing.
    * **Tool use**: To extract specific information from documents for use as tool inputs.

  </Step>
</Steps>

### Estimate your costs

The token count of a PDF file depends on the total text extracted from the document as well as the number of pages:

- Text token costs: Each page typically uses 1,500-3,000 tokens per page depending on content density. Standard API pricing applies with no additional PDF fees.
- Image token costs: Since each page is converted into an image, the same [image-based cost calculations](/en/docs/build-with-claude/vision#evaluate-image-size) are applied.

You can use [token counting](/en/docs/build-with-claude/token-counting) to estimate costs for your specific PDFs.

---

## Optimize PDF processing

### Improve performance

Follow these best practices for optimal results:

- Place PDFs before text in your requests
- Use standard fonts
- Ensure text is clear and legible
- Rotate pages to proper upright orientation
- Use logical page numbers (from PDF viewer) in prompts
- Split large PDFs into chunks when needed
- Enable prompt caching for repeated analysis

### Scale your implementation

For high-volume processing, consider these approaches:

#### Use prompt caching

Cache PDFs to improve performance on repeated queries:

<CodeGroup>
  ```bash Shell
  # Create a JSON request file using the pdf_base64.txt content
  jq -n --rawfile PDF_BASE64 pdf_base64.txt '{
      "model": "claude-opus-4-20250514",
      "max_tokens": 1024,
      "messages": [{
          "role": "user",
          "content": [{
              "type": "document",
              "source": {
                  "type": "base64",
                  "media_type": "application/pdf",
                  "data": $PDF_BASE64
              },
              "cache_control": {
                "type": "ephemeral"
              }
          },
          {
              "type": "text",
              "text": "Which model has the highest human preference win rates across each use-case?"
          }]
      }]
  }' > request.json

# Then make the API call using the JSON file

curl https://api.anthropic.com/v1/messages \
 -H "content-type: application/json" \
 -H "x-api-key: $ANTHROPIC_API_KEY" \
 -H "anthropic-version: 2023-06-01" \
 -d @request.json

````

```python Python
message = client.messages.create(
    model="claude-opus-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data
                    },
                    "cache_control": {"type": "ephemeral"}
                },
                {
                    "type": "text",
                    "text": "Analyze this document."
                }
            ]
        }
    ],
)
````

```TypeScript TypeScript
const response = await anthropic.messages.create({
  model: 'claude-opus-4-20250514',
  max_tokens: 1024,
  messages: [
    {
      content: [
        {
          type: 'document',
          source: {
            media_type: 'application/pdf',
            type: 'base64',
            data: pdfBase64,
          },
          cache_control: { type: 'ephemeral' },
        },
        {
          type: 'text',
          text: 'Which model has the highest human preference win rates across each use-case?',
        },
      ],
      role: 'user',
    },
  ],
});
console.log(response);
```

```java Java
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.Base64PdfSource;
import com.anthropic.models.messages.CacheControlEphemeral;
import com.anthropic.models.messages.ContentBlockParam;
import com.anthropic.models.messages.DocumentBlockParam;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.TextBlockParam;

public class MessagesDocumentExample {

    public static void main(String[] args) throws IOException {
        AnthropicClient client = AnthropicOkHttpClient.fromEnv();

        // Read PDF file as base64
        byte[] pdfBytes = Files.readAllBytes(Paths.get("pdf_base64.txt"));
        String pdfBase64 = new String(pdfBytes);

        MessageCreateParams params = MessageCreateParams.builder()
                .model(Model.CLAUDE_OPUS_4_20250514)
                .maxTokens(1024)
                .addUserMessageOfBlockParams(List.of(
                        ContentBlockParam.ofDocument(
                                DocumentBlockParam.builder()
                                        .source(Base64PdfSource.builder()
                                                .data(pdfBase64)
                                                .build())
                                        .cacheControl(CacheControlEphemeral.builder().build())
                                        .build()),
                        ContentBlockParam.ofText(
                                TextBlockParam.builder()
                                        .text("Which model has the highest human preference win rates across each use-case?")
                                        .build())
                ))
                .build();


        Message message = client.messages().create(params);
        System.out.println(message);
    }
}
```

</CodeGroup>

#### Process document batches

Use the Message Batches API for high-volume workflows:

<CodeGroup>
  ```bash Shell
  # Create a JSON request file using the pdf_base64.txt content
  jq -n --rawfile PDF_BASE64 pdf_base64.txt '
  {
    "requests": [
        {
            "custom_id": "my-first-request",
            "params": {
                "model": "claude-opus-4-20250514",
                "max_tokens": 1024,
                "messages": [
                  {
                      "role": "user",
                      "content": [
                          {
                              "type": "document",
                              "source": {
                                  "type": "base64",
                                  "media_type": "application/pdf",
                                  "data": $PDF_BASE64
                              }
                          },
                          {
                              "type": "text",
                              "text": "Which model has the highest human preference win rates across each use-case?"
                          }
                      ]
                  }
                ]
            }
        },
        {
            "custom_id": "my-second-request",
            "params": {
                "model": "claude-opus-4-20250514",
                "max_tokens": 1024,
                "messages": [
                  {
                      "role": "user",
                      "content": [
                          {
                              "type": "document",
                              "source": {
                                  "type": "base64",
                                  "media_type": "application/pdf",
                                  "data": $PDF_BASE64
                              }
                          },
                          {
                              "type": "text",
                              "text": "Extract 5 key insights from this document."
                          }
                      ]
                  }
                ]
            }
        }
    ]
  }
  ' > request.json

# Then make the API call using the JSON file

curl https://api.anthropic.com/v1/messages/batches \
 -H "content-type: application/json" \
 -H "x-api-key: $ANTHROPIC_API_KEY" \
 -H "anthropic-version: 2023-06-01" \
 -d @request.json

````

```python Python
message_batch = client.messages.batches.create(
    requests=[
        {
            "custom_id": "doc1",
            "params": {
                "model": "claude-opus-4-20250514",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_data
                                }
                            },
                            {
                                "type": "text",
                                "text": "Summarize this document."
                            }
                        ]
                    }
                ]
            }
        }
    ]
)
````

```TypeScript TypeScript
const response = await anthropic.messages.batches.create({
  requests: [
    {
      custom_id: 'my-first-request',
      params: {
        max_tokens: 1024,
        messages: [
          {
            content: [
              {
                type: 'document',
                source: {
                  media_type: 'application/pdf',
                  type: 'base64',
                  data: pdfBase64,
                },
              },
              {
                type: 'text',
                text: 'Which model has the highest human preference win rates across each use-case?',
              },
            ],
            role: 'user',
          },
        ],
        model: 'claude-opus-4-20250514',
      },
    },
    {
      custom_id: 'my-second-request',
      params: {
        max_tokens: 1024,
        messages: [
          {
            content: [
              {
                type: 'document',
                source: {
                  media_type: 'application/pdf',
                  type: 'base64',
                  data: pdfBase64,
                },
              },
              {
                type: 'text',
                text: 'Extract 5 key insights from this document.',
              },
            ],
            role: 'user',
          },
        ],
        model: 'claude-opus-4-20250514',
      },
    }
  ],
});
console.log(response);
```

```java Java
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.*;
import com.anthropic.models.messages.batches.*;

public class MessagesBatchDocumentExample {

    public static void main(String[] args) throws IOException {
        AnthropicClient client = AnthropicOkHttpClient.fromEnv();

        // Read PDF file as base64
        byte[] pdfBytes = Files.readAllBytes(Paths.get("pdf_base64.txt"));
        String pdfBase64 = new String(pdfBytes);

        BatchCreateParams params = BatchCreateParams.builder()
                .addRequest(BatchCreateParams.Request.builder()
                        .customId("my-first-request")
                        .params(BatchCreateParams.Request.Params.builder()
                                .model(Model.CLAUDE_OPUS_4_20250514)
                                .maxTokens(1024)
                                .addUserMessageOfBlockParams(List.of(
                                        ContentBlockParam.ofDocument(
                                                DocumentBlockParam.builder()
                                                        .source(Base64PdfSource.builder()
                                                                .data(pdfBase64)
                                                                .build())
                                                        .build()
                                        ),
                                        ContentBlockParam.ofText(
                                                TextBlockParam.builder()
                                                        .text("Which model has the highest human preference win rates across each use-case?")
                                                        .build()
                                        )
                                ))
                                .build())
                        .build())
                .addRequest(BatchCreateParams.Request.builder()
                        .customId("my-second-request")
                        .params(BatchCreateParams.Request.Params.builder()
                                .model(Model.CLAUDE_OPUS_4_20250514)
                                .maxTokens(1024)
                                .addUserMessageOfBlockParams(List.of(
                                        ContentBlockParam.ofDocument(
                                        DocumentBlockParam.builder()
                                                .source(Base64PdfSource.builder()
                                                        .data(pdfBase64)
                                                        .build())
                                                .build()
                                        ),
                                        ContentBlockParam.ofText(
                                                TextBlockParam.builder()
                                                        .text("Extract 5 key insights from this document.")
                                                        .build()
                                        )
                                ))
                                .build())
                        .build())
                .build();

        MessageBatch batch = client.messages().batches().create(params);
        System.out.println(batch);
    }
}
```

</CodeGroup>

## Next steps

<CardGroup cols={2}>
  <Card title="Try PDF examples" icon="file-pdf" href="https://github.com/anthropics/anthropic-cookbook/tree/main/multimodal">
    Explore practical examples of PDF processing in our cookbook recipe.
  </Card>

  <Card title="View API reference" icon="code" href="/en/api/messages">
    See complete API documentation for PDF support.
  </Card>
</CardGroup>

Files API:

# Files API

The Files API lets you upload and manage files to use with the Anthropic API without re-uploading content with each request. This is particularly useful when using the [code execution tool](/en/docs/agents-and-tools/tool-use/code-execution-tool) to provide inputs (e.g. datasets and documents) and then download outputs (e.g. charts). You can also use the Files API to prevent having to continually re-upload frequently used documents and images across multiple API calls.

<Note>
  The Files API is currently in beta. Please reach out through our [feedback form](https://forms.gle/tisHyierGwgN4DUE9) to share your experience with the Files API.
</Note>

## Supported models

Referencing a `file_id` in a Messages request is supported in all models that support the given file type. For example, [images](/en/docs/build-with-claude/vision) are supported in all Claude 3+ models, [PDFs](/en/docs/build-with-claude/pdf-support) in all Claude 3.5+ models, and [various other file types](/en/docs/agents-and-tools/tool-use/code-execution-tool#supported-file-types) for the code execution tool in Claude 3.5 Haiku plus all Claude 3.7+ models.

The Files API is currently not supported on Amazon Bedrock or Google Vertex AI.

## How the Files API works

The Files API provides a simple create-once, use-many-times approach for working with files:

- **Upload files** to our secure storage and receive a unique `file_id`
- **Download files** that are created from the code execution tool
- **Reference files** in [Messages](/en/api/messages) requests using the `file_id` instead of re-uploading content
- **Manage your files** with list, retrieve, and delete operations

## How to use the Files API

<Note>
  To use the Files API, you'll need to include the beta feature header: `anthropic-beta: files-api-2025-04-14`.
</Note>

### Uploading a file

Upload a file to be referenced in future API calls:

<CodeGroup>
  ```bash Shell
  curl -X POST https://api.anthropic.com/v1/files \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: files-api-2025-04-14" \
    -F "file=@/path/to/document.pdf"
  ```

```python Python
import anthropic

client = anthropic.Anthropic()
client.beta.files.upload(
  file=("document.pdf", open("/path/to/document.pdf", "rb"), "application/pdf"),
)
```

```typescript TypeScript
import Anthropic, { toFile } from "@anthropic-ai/sdk";
import fs from "fs";

const anthropic = new Anthropic();

await anthropic.beta.files.upload(
  {
    file: await toFile(
      fs.createReadStream("/path/to/document.pdf"),
      undefined,
      { type: "application/pdf" }
    ),
  },
  {
    betas: ["files-api-2025-04-14"],
  }
);
```

</CodeGroup>

### Using a file in messages

Once uploaded, reference the file using its `file_id`:

<CodeGroup>
  ```bash Shell
  curl -X POST https://api.anthropic.com/v1/messages \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: files-api-2025-04-14" \
    -H "content-type: application/json" \
    -d '{
      "model": "claude-sonnet-4-20250514",
      "max_tokens": 1024,
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "Please summarize this document for me."          
            },
            {
              "type": "document",
              "source": {
                "type": "file",
                "file_id": "file_011CNha8iCJcU1wXNR6q4V8w"
              }
            }
          ]
        }
      ]
    }'
  ```

```python Python
import anthropic

client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Please summarize this document for me."
                },
                {
                    "type": "document",
                    "source": {
                        "type": "file",
                        "file_id": "file_011CNha8iCJcU1wXNR6q4V8w"
                    }
                }
            ]
        }
    ],
    betas=["files-api-2025-04-14"],
)
print(response)
```

```typescript TypeScript
import { Anthropic } from "@anthropic-ai/sdk";

const anthropic = new Anthropic();

const response = await anthropic.beta.messages.create({
  model: "claude-sonnet-4-20250514",
  max_tokens: 1024,
  messages: [
    {
      role: "user",
      content: [
        {
          type: "text",
          text: "Please summarize this document for me.",
        },
        {
          type: "document",
          source: {
            type: "file",
            file_id: "file_011CNha8iCJcU1wXNR6q4V8w",
          },
        },
      ],
    },
  ],
  betas: ["files-api-2025-04-14"],
});

console.log(response);
```

</CodeGroup>

### File types and content blocks

The Files API supports different file types that correspond to different content block types:

| File Type                                                                                       | MIME Type                                            | Content Block Type | Use Case                            |
| :---------------------------------------------------------------------------------------------- | :--------------------------------------------------- | :----------------- | :---------------------------------- |
| PDF                                                                                             | `application/pdf`                                    | `document`         | Text analysis, document processing  |
| Plain text                                                                                      | `text/plain`                                         | `document`         | Text analysis, processing           |
| Images                                                                                          | `image/jpeg`, `image/png`, `image/gif`, `image/webp` | `image`            | Image analysis, visual tasks        |
| [Datasets, others](/en/docs/agents-and-tools/tool-use/code-execution-tool#supported-file-types) | Varies                                               | `container_upload` | Analyze data, create visualizations |

### Working with other file formats

For file types that are not supported as `document` blocks (.csv, .txt, .md, .docx, .xlsx), convert the files to plain text, and include the content directly in your message:

<CodeGroup>
  ```bash Shell
  # Example: Reading a text file and sending it as plain text
  # Note: For files with special characters, consider base64 encoding
  TEXT_CONTENT=$(cat document.txt | jq -Rs .)

curl https://api.anthropic.com/v1/messages \
 -H "content-type: application/json" \
 -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -d @- <<EOF
  {
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Here's the document content:\n\n${TEXT_CONTENT}\n\nPlease summarize this document."
}
]
}
]
}
EOF

````

```python Python
import pandas as pd
import anthropic

client = anthropic.Anthropic()

# Example: Reading a CSV file
df = pd.read_csv('data.csv')
csv_content = df.to_string()

# Send as plain text in the message
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Here's the CSV data:\n\n{csv_content}\n\nPlease analyze this data."
                }
            ]
        }
    ]
)

print(response.content[0].text)
````

```typescript TypeScript
import { Anthropic } from "@anthropic-ai/sdk";
import fs from "fs";

const anthropic = new Anthropic();

async function analyzeDocument() {
  // Example: Reading a text file
  const textContent = fs.readFileSync("document.txt", "utf-8");

  // Send as plain text in the message
  const response = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: [
          {
            type: "text",
            text: `Here's the document content:\n\n${textContent}\n\nPlease summarize this document.`,
          },
        ],
      },
    ],
  });

  console.log(response.content[0].text);
}

analyzeDocument();
```

</CodeGroup>

<Note>
  For .docx files containing images, convert them to PDF format first, then use [PDF support](/en/docs/build-with-claude/pdf-support) to take advantage of the built-in image parsing. This allows using citations from the PDF document.
</Note>

#### Document blocks

For PDFs and text files, use the `document` content block:

```json
{
  "type": "document",
  "source": {
    "type": "file",
    "file_id": "file_011CNha8iCJcU1wXNR6q4V8w"
  },
  "title": "Document Title", // Optional
  "context": "Context about the document", // Optional
  "citations": { "enabled": true } // Optional, enables citations
}
```

#### Image blocks

For images, use the `image` content block:

```json
{
  "type": "image",
  "source": {
    "type": "file",
    "file_id": "file_011CPMxVD3fHLUhvTqtsQA5w"
  }
}
```

### Managing files

#### List files

Retrieve a list of your uploaded files:

<CodeGroup>
  ```bash Shell
  curl https://api.anthropic.com/v1/files \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: files-api-2025-04-14"
  ```

```python Python
import anthropic

client = anthropic.Anthropic()
files = client.beta.files.list()
```

```typescript TypeScript
import { Anthropic } from "@anthropic-ai/sdk";

const anthropic = new Anthropic();
const files = await anthropic.beta.files.list({
  betas: ["files-api-2025-04-14"],
});
```

</CodeGroup>

#### Get file metadata

Retrieve information about a specific file:

<CodeGroup>
  ```bash Shell
  curl https://api.anthropic.com/v1/files/file_011CNha8iCJcU1wXNR6q4V8w \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: files-api-2025-04-14"
  ```

```python Python
import anthropic

client = anthropic.Anthropic()
file = client.beta.files.retrieve_metadata("file_011CNha8iCJcU1wXNR6q4V8w")
```

```typescript TypeScript
import { Anthropic } from "@anthropic-ai/sdk";

const anthropic = new Anthropic();
const file = await anthropic.beta.files.retrieveMetadata(
  "file_011CNha8iCJcU1wXNR6q4V8w",
  { betas: ["files-api-2025-04-14"] }
);
```

</CodeGroup>

#### Delete a file

Remove a file from your workspace:

<CodeGroup>
  ```bash Shell
  curl -X DELETE https://api.anthropic.com/v1/files/file_011CNha8iCJcU1wXNR6q4V8w \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: files-api-2025-04-14"
  ```

```python Python
import anthropic

client = anthropic.Anthropic()
result = client.beta.files.delete("file_011CNha8iCJcU1wXNR6q4V8w")
```

```typescript TypeScript
import { Anthropic } from "@anthropic-ai/sdk";

const anthropic = new Anthropic();
const result = await anthropic.beta.files.delete(
  "file_011CNha8iCJcU1wXNR6q4V8w",
  { betas: ["files-api-2025-04-14"] }
);
```

</CodeGroup>

### Downloading a file

Download files that have been created by the code execution tool:

<CodeGroup>
  ```bash Shell
  curl -X GET "https://api.anthropic.com/v1/files/file_011CNha8iCJcU1wXNR6q4V8w/content" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: files-api-2025-04-14" \
    --output downloaded_file.txt
  ```

```python Python
import anthropic

client = anthropic.Anthropic()
file_content = client.beta.files.download("file_011CNha8iCJcU1wXNR6q4V8w")

# Save to file
with open("downloaded_file.txt", "w") as f:
    f.write(file_content.decode('utf-8'))
```

```typescript TypeScript
import { Anthropic } from "@anthropic-ai/sdk";
import fs from "fs";

const anthropic = new Anthropic();

const fileContent = await anthropic.beta.files.download(
  "file_011CNha8iCJcU1wXNR6q4V8w",
  { betas: ["files-api-2025-04-14"] }
);

// Save to file
fs.writeFileSync("downloaded_file.txt", fileContent);
```

</CodeGroup>

<Note>
  You can only download files that were created by the [code execution tool](/en/docs/agents-and-tools/tool-use/code-execution-tool). Files that you uploaded cannot be downloaded.
</Note>

---

## File storage and limits

### Storage limits

- **Maximum file size:** 500 MB per file
- **Total storage:** 100 GB per organization

### File lifecycle

- Files are scoped to the workspace of the API key. Other API keys can use files created by any other API key associated with the same workspace
- Files persist until you delete them
- Deleted files cannot be recovered
- Files are inaccessible via the API shortly after deletion, but they may persist in active `Messages` API calls and associated tool uses

---

## Error handling

Common errors when using the Files API include:

- **File not found (404):** The specified `file_id` doesn't exist or you don't have access to it
- **Invalid file type (400):** The file type doesn't match the content block type (e.g., using an image file in a document block)
- **Exceeds context window size (400):** The file is larger than the context window size (e.g. using a 500 MB plaintext file in a `/v1/messages` request)
- **Invalid filename (400):** Filename doesn't meet the length requirements (1-255 characters) or contains forbidden characters (`<`, `>`, `:`, `"`, `|`, `?`, `*`, `\`, `/`, or unicode characters 0-31)
- **File too large (413):** File exceeds the 500 MB limit
- **Storage limit exceeded (403):** Your organization has reached the 100 GB storage limit

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "File not found: file_011CNha8iCJcU1wXNR6q4V8w"
  }
}
```

## Usage and billing

File API operations are **free**:

- Uploading files
- Downloading files
- Listing files
- Getting file metadata
- Deleting files

File content used in `Messages` requests are priced as input tokens. You can only download files created by the code execution tool.

### Rate limits

During the beta period:

- File-related API calls are limited to approximately 100 requests per minute
- [Contact us](mailto:sales@anthropic.com) if you need higher limits for your use case

///////

# Vision

> The Claude 3 and 4 families of models comes with new vision capabilities that allow Claude to understand and analyze images, opening up exciting possibilities for multimodal interaction.

This guide describes how to work with images in Claude, including best practices, code examples, and limitations to keep in mind.

---

## How to use vision

Use Claude’s vision capabilities via:

- [claude.ai](https://claude.ai/). Upload an image like you would a file, or drag and drop an image directly into the chat window.
- The [Console Workbench](https://console.anthropic.com/workbench/). If you select a model that accepts images (Claude 3 and 4 models only), a button to add images appears at the top right of every User message block.
- **API request**. See the examples in this guide.

---

## Before you upload

### Basics and Limits

You can include multiple images in a single request (up to 20 for [claude.ai](https://claude.ai/) and 100 for API requests). Claude will analyze all provided images when formulating its response. This can be helpful for comparing or contrasting images.

If you submit an image larger than 8000x8000 px, it will be rejected. If you submit more than 20 images in one API request, this limit is 2000x2000 px.

### Evaluate image size

For optimal performance, we recommend resizing images before uploading if they are too large. If your image’s long edge is more than 1568 pixels, or your image is more than \~1,600 tokens, it will first be scaled down, preserving aspect ratio, until it’s within the size limits.

If your input image is too large and needs to be resized, it will increase latency of [time-to-first-token](/en/docs/about-claude/glossary), without giving you any additional model performance. Very small images under 200 pixels on any given edge may degrade performance.

<Tip>
  To improve [time-to-first-token](/en/docs/about-claude/glossary), we recommend
  resizing images to no more than 1.15 megapixels (and within 1568 pixels in
  both dimensions).
</Tip>

Here is a table of maximum image sizes accepted by our API that will not be resized for common aspect ratios. With the Claude Sonnet 3.7 model, these images use approximately 1,600 tokens and around \$4.80/1K images.

| Aspect ratio | Image size   |
| ------------ | ------------ |
| 1:1          | 1092x1092 px |
| 3:4          | 951x1268 px  |
| 2:3          | 896x1344 px  |
| 9:16         | 819x1456 px  |
| 1:2          | 784x1568 px  |

### Calculate image costs

Each image you include in a request to Claude counts towards your token usage. To calculate the approximate cost, multiply the approximate number of image tokens by the [per-token price of the model](https://anthropic.com/pricing) you’re using.

If your image does not need to be resized, you can estimate the number of tokens used through this algorithm: `tokens = (width px * height px)/750`

Here are examples of approximate tokenization and costs for different image sizes within our API’s size constraints based on Claude Sonnet 3.7 per-token price of \$3 per million input tokens:

| Image size                    | # of Tokens | Cost / image | Cost / 1K images |
| ----------------------------- | ----------- | ------------ | ---------------- |
| 200x200 px(0.04 megapixels)   | \~54        | \~\$0.00016  | \~\$0.16         |
| 1000x1000 px(1 megapixel)     | \~1334      | \~\$0.004    | \~\$4.00         |
| 1092x1092 px(1.19 megapixels) | \~1590      | \~\$0.0048   | \~\$4.80         |

### Ensuring image quality

When providing images to Claude, keep the following in mind for best results:

- **Image format**: Use a supported image format: JPEG, PNG, GIF, or WebP.
- **Image clarity**: Ensure images are clear and not too blurry or pixelated.
- **Text**: If the image contains important text, make sure it’s legible and not too small. Avoid cropping out key visual context just to enlarge the text.

---

## Prompt examples

Many of the [prompting techniques](/en/docs/build-with-claude/prompt-engineering/overview) that work well for text-based interactions with Claude can also be applied to image-based prompts.

These examples demonstrate best practice prompt structures involving images.

<Tip>
  Just as with document-query placement, Claude works best when images come
  before text. Images placed after text or interpolated with text will still
  perform well, but if your use case allows it, we recommend an image-then-text
  structure.
</Tip>

### About the prompt examples

The following examples demonstrate how to use Claude's vision capabilities using various programming languages and approaches. You can provide images to Claude in three ways:

1. As a base64-encoded image in `image` content blocks
2. As a URL reference to an image hosted online
3. Using the Files API (upload once, use multiple times)

The base64 example prompts use these variables:

<CodeGroup>
  ```bash Shell
      # For URL-based images, you can use the URL directly in your JSON request
      
      # For base64-encoded images, you need to first encode the image
      # Example of how to encode an image to base64 in bash:
      BASE64_IMAGE_DATA=$(curl -s "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg" | base64)
      
      # The encoded data can now be used in your API calls
  ```

```Python Python
import base64
import httpx

# For base64-encoded images
image1_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
image1_media_type = "image/jpeg"
image1_data = base64.standard_b64encode(httpx.get(image1_url).content).decode("utf-8")

image2_url = "https://upload.wikimedia.org/wikipedia/commons/b/b5/Iridescent.green.sweat.bee1.jpg"
image2_media_type = "image/jpeg"
image2_data = base64.standard_b64encode(httpx.get(image2_url).content).decode("utf-8")

# For URL-based images, you can use the URLs directly in your requests
```

```TypeScript TypeScript
import axios from 'axios';

// For base64-encoded images
async function getBase64Image(url: string): Promise<string> {
  const response = await axios.get(url, { responseType: 'arraybuffer' });
  return Buffer.from(response.data, 'binary').toString('base64');
}

// Usage
async function prepareImages() {
  const imageData = await getBase64Image('https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg');
  // Now you can use imageData in your API calls
}

// For URL-based images, you can use the URLs directly in your requests
```

```java Java
import java.io.IOException;
import java.util.Base64;
import java.io.InputStream;
import java.net.URL;

public class ImageHandlingExample {

    public static void main(String[] args) throws IOException, InterruptedException {
        // For base64-encoded images
        String image1Url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg";
        String image1MediaType = "image/jpeg";
        String image1Data = downloadAndEncodeImage(image1Url);

        String image2Url = "https://upload.wikimedia.org/wikipedia/commons/b/b5/Iridescent.green.sweat.bee1.jpg";
        String image2MediaType = "image/jpeg";
        String image2Data = downloadAndEncodeImage(image2Url);

        // For URL-based images, you can use the URLs directly in your requests
    }

    private static String downloadAndEncodeImage(String imageUrl) throws IOException {
        try (InputStream inputStream = new URL(imageUrl).openStream()) {
            return Base64.getEncoder().encodeToString(inputStream.readAllBytes());
        }
    }

}
```

</CodeGroup>

Below are examples of how to include images in a Messages API request using base64-encoded images and URL references:

### Base64-encoded image example

<CodeGroup>
  ```bash Shell
  curl https://api.anthropic.com/v1/messages \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d '{
      "model": "claude-sonnet-4-20250514",
      "max_tokens": 1024,
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "image",
              "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": "'"$BASE64_IMAGE_DATA"'"
              }
            },
            {
              "type": "text",
              "text": "Describe this image."
            }
          ]
        }
      ]
    }'
  ```

```Python Python
import anthropic

client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image1_media_type,
                        "data": image1_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Describe this image."
                }
            ],
        }
    ],
)
print(message)
```

```TypeScript TypeScript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

async function main() {
  const message = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: [
          {
            type: "image",
            source: {
              type: "base64",
              media_type: "image/jpeg",
              data: imageData, // Base64-encoded image data as string
            }
          },
          {
            type: "text",
            text: "Describe this image."
          }
        ]
      }
    ]
  });

  console.log(message);
}

main();
```

```Java Java
import java.io.IOException;
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.*;

public class VisionExample {
    public static void main(String[] args) throws IOException, InterruptedException {
        AnthropicClient client = AnthropicOkHttpClient.fromEnv();
        String imageData = ""; // // Base64-encoded image data as string

        List<ContentBlockParam> contentBlockParams = List.of(
                ContentBlockParam.ofImage(
                        ImageBlockParam.builder()
                                .source(Base64ImageSource.builder()
                                        .data(imageData)
                                        .build())
                                .build()
                ),
                ContentBlockParam.ofText(TextBlockParam.builder()
                        .text("Describe this image.")
                        .build())
        );
        Message message = client.messages().create(
                MessageCreateParams.builder()
                        .model(Model.CLAUDE_3_7_SONNET_LATEST)
                        .maxTokens(1024)
                        .addUserMessageOfBlockParams(contentBlockParams)
                        .build()
        );

        System.out.println(message);
    }
}
```

</CodeGroup>

### URL-based image example

<CodeGroup>
  ```bash Shell
  curl https://api.anthropic.com/v1/messages \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d '{
      "model": "claude-sonnet-4-20250514",
      "max_tokens": 1024,
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "image",
              "source": {
                "type": "url",
                "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
              }
            },
            {
              "type": "text",
              "text": "Describe this image."
            }
          ]
        }
      ]
    }'
  ```

```Python Python
import anthropic

client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
                    },
                },
                {
                    "type": "text",
                    "text": "Describe this image."
                }
            ],
        }
    ],
)
print(message)
```

```TypeScript TypeScript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

async function main() {
  const message = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: [
          {
            type: "image",
            source: {
              type: "url",
              url: "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
            }
          },
          {
            type: "text",
            text: "Describe this image."
          }
        ]
      }
    ]
  });

  console.log(message);
}

main();
```

```Java Java
import java.io.IOException;
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.*;

public class VisionExample {

    public static void main(String[] args) throws IOException, InterruptedException {
        AnthropicClient client = AnthropicOkHttpClient.fromEnv();

        List<ContentBlockParam> contentBlockParams = List.of(
                ContentBlockParam.ofImage(
                        ImageBlockParam.builder()
                                .source(UrlImageSource.builder()
                                        .url("https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg")
                                        .build())
                                .build()
                ),
                ContentBlockParam.ofText(TextBlockParam.builder()
                        .text("Describe this image.")
                        .build())
        );
        Message message = client.messages().create(
                MessageCreateParams.builder()
                        .model(Model.CLAUDE_3_7_SONNET_LATEST)
                        .maxTokens(1024)
                        .addUserMessageOfBlockParams(contentBlockParams)
                        .build()
        );
        System.out.println(message);
    }
}
```

</CodeGroup>

### Files API image example

For images you'll use repeatedly or when you want to avoid encoding overhead, use the [Files API](/en/docs/build-with-claude/files):

<CodeGroup>
  ```bash Shell
  # First, upload your image to the Files API
  curl -X POST https://api.anthropic.com/v1/files \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: files-api-2025-04-14" \
    -F "file=@image.jpg"

# Then use the returned file_id in your message

curl https://api.anthropic.com/v1/messages \
 -H "x-api-key: $ANTHROPIC_API_KEY" \
 -H "anthropic-version: 2023-06-01" \
 -H "anthropic-beta: files-api-2025-04-14" \
 -H "content-type: application/json" \
 -d '{
"model": "claude-sonnet-4-20250514",
"max_tokens": 1024,
"messages": [
{
"role": "user",
"content": [
{
"type": "image",
"source": {
"type": "file",
"file_id": "file_abc123"
}
},
{
"type": "text",
"text": "Describe this image."
}
]
}
]
}'

````

```python Python
import anthropic

client = anthropic.Anthropic()

# Upload the image file
with open("image.jpg", "rb") as f:
    file_upload = client.beta.files.upload(file=("image.jpg", f, "image/jpeg"))

# Use the uploaded file in a message
message = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    betas=["files-api-2025-04-14"],
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "file",
                        "file_id": file_upload.id
                    }
                },
                {
                    "type": "text",
                    "text": "Describe this image."
                }
            ]
        }
    ],
)

print(message.content)
````

```typescript TypeScript
import { Anthropic, toFile } from "@anthropic-ai/sdk";
import fs from "fs";

const anthropic = new Anthropic();

async function main() {
  // Upload the image file
  const fileUpload = await anthropic.beta.files.upload(
    {
      file: toFile(fs.createReadStream("image.jpg"), undefined, {
        type: "image/jpeg",
      }),
    },
    {
      betas: ["files-api-2025-04-14"],
    }
  );

  // Use the uploaded file in a message
  const response = await anthropic.beta.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1024,
    betas: ["files-api-2025-04-14"],
    messages: [
      {
        role: "user",
        content: [
          {
            type: "image",
            source: {
              type: "file",
              file_id: fileUpload.id,
            },
          },
          {
            type: "text",
            text: "Describe this image.",
          },
        ],
      },
    ],
  });

  console.log(response);
}

main();
```

```java Java
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.File;
import com.anthropic.models.files.FileUploadParams;
import com.anthropic.models.messages.*;

public class ImageFilesExample {
    public static void main(String[] args) throws IOException {
        AnthropicClient client = AnthropicOkHttpClient.fromEnv();

        // Upload the image file
        File file = client.beta().files().upload(FileUploadParams.builder()
                .file(Files.newInputStream(Path.of("image.jpg")))
                .build());

        // Use the uploaded file in a message
        ImageBlockParam imageParam = ImageBlockParam.builder()
                .fileSource(file.id())
                .build();

        MessageCreateParams params = MessageCreateParams.builder()
                .model(Model.CLAUDE_3_7_SONNET_LATEST)
                .maxTokens(1024)
                .addUserMessageOfBlockParams(
                        List.of(
                                ContentBlockParam.ofImage(imageParam),
                                ContentBlockParam.ofText(
                                        TextBlockParam.builder()
                                                .text("Describe this image.")
                                                .build()
                                )
                        )
                )
                .build();

        Message message = client.messages().create(params);
        System.out.println(message.content());
    }
}
```

</CodeGroup>

See [Messages API examples](/en/api/messages) for more example code and parameter details.

<AccordionGroup>
  <Accordion title="Example: One image">
    It’s best to place images earlier in the prompt than questions about them or instructions for tasks that use them.

    Ask Claude to describe one image.

    | Role | Content                       |
    | ---- | ----------------------------- |
    | User | \[Image] Describe this image. |

    Here is the corresponding API call using the Claude Sonnet 3.7 model.

    <Tabs>
      <Tab title="Using Base64">
        ```Python Python
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image1_media_type,
                                "data": image1_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Describe this image."
                        }
                    ],
                }
            ],
        )
        ```
      </Tab>

      <Tab title="Using URL">
        ```Python Python
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "url",
                                "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Describe this image."
                        }
                    ],
                }
            ],
        )
        ```
      </Tab>
    </Tabs>

  </Accordion>

  <Accordion title="Example: Multiple images">
    In situations where there are multiple images, introduce each image with `Image 1:` and `Image 2:` and so on. You don’t need newlines between images or between images and the prompt.

    Ask Claude to describe the differences between multiple images.

    | Role | Content                                                                 |
    | ---- | ----------------------------------------------------------------------- |
    | User | Image 1: \[Image 1] Image 2: \[Image 2] How are these images different? |

    Here is the corresponding API call using the Claude Sonnet 3.7 model.

    <Tabs>
      <Tab title="Using Base64">
        ```Python Python
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Image 1:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image1_media_type,
                                "data": image1_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Image 2:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image2_media_type,
                                "data": image2_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "How are these images different?"
                        }
                    ],
                }
            ],
        )
        ```
      </Tab>

      <Tab title="Using URL">
        ```Python Python
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Image 1:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "url",
                                "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Image 2:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "url",
                                "url": "https://upload.wikimedia.org/wikipedia/commons/b/b5/Iridescent.green.sweat.bee1.jpg",
                            },
                        },
                        {
                            "type": "text",
                            "text": "How are these images different?"
                        }
                    ],
                }
            ],
        )
        ```
      </Tab>
    </Tabs>

  </Accordion>

  <Accordion title="Example: Multiple images with a system prompt">
    Ask Claude to describe the differences between multiple images, while giving it a system prompt for how to respond.

    | Content |                                                                         |
    | ------- | ----------------------------------------------------------------------- |
    | System  | Respond only in Spanish.                                                |
    | User    | Image 1: \[Image 1] Image 2: \[Image 2] How are these images different? |

    Here is the corresponding API call using the Claude Sonnet 3.7 model.

    <Tabs>
      <Tab title="Using Base64">
        ```Python Python
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="Respond only in Spanish.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Image 1:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image1_media_type,
                                "data": image1_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Image 2:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image2_media_type,
                                "data": image2_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "How are these images different?"
                        }
                    ],
                }
            ],
        )
        ```
      </Tab>

      <Tab title="Using URL">
        ```Python Python
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="Respond only in Spanish.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Image 1:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "url",
                                "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Image 2:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "url",
                                "url": "https://upload.wikimedia.org/wikipedia/commons/b/b5/Iridescent.green.sweat.bee1.jpg",
                            },
                        },
                        {
                            "type": "text",
                            "text": "How are these images different?"
                        }
                    ],
                }
            ],
        )
        ```
      </Tab>
    </Tabs>

  </Accordion>

  <Accordion title="Example: Four images across two conversation turns">
    Claude’s vision capabilities shine in multimodal conversations that mix images and text. You can have extended back-and-forth exchanges with Claude, adding new images or follow-up questions at any point. This enables powerful workflows for iterative image analysis, comparison, or combining visuals with other knowledge.

    Ask Claude to contrast two images, then ask a follow-up question comparing the first images to two new images.

    | Role      | Content                                                                            |
    | --------- | ---------------------------------------------------------------------------------- |
    | User      | Image 1: \[Image 1] Image 2: \[Image 2] How are these images different?            |
    | Assistant | \[Claude's response]                                                               |
    | User      | Image 1: \[Image 3] Image 2: \[Image 4] Are these images similar to the first two? |
    | Assistant | \[Claude's response]                                                               |

    When using the API, simply insert new images into the array of Messages in the `user` role as part of any standard [multiturn conversation](/en/api/messages-examples#multiple-conversational-turns) structure.

  </Accordion>
</AccordionGroup>

---

## Limitations

While Claude's image understanding capabilities are cutting-edge, there are some limitations to be aware of:

- **People identification**: Claude [cannot be used](https://www.anthropic.com/legal/aup) to identify (i.e., name) people in images and will refuse to do so.
- **Accuracy**: Claude may hallucinate or make mistakes when interpreting low-quality, rotated, or very small images under 200 pixels.
- **Spatial reasoning**: Claude's spatial reasoning abilities are limited. It may struggle with tasks requiring precise localization or layouts, like reading an analog clock face or describing exact positions of chess pieces.
- **Counting**: Claude can give approximate counts of objects in an image but may not always be precisely accurate, especially with large numbers of small objects.
- **AI generated images**: Claude does not know if an image is AI-generated and may be incorrect if asked. Do not rely on it to detect fake or synthetic images.
- **Inappropriate content**: Claude will not process inappropriate or explicit images that violate our [Acceptable Use Policy](https://www.anthropic.com/legal/aup).
- **Healthcare applications**: While Claude can analyze general medical images, it is not designed to interpret complex diagnostic scans such as CTs or MRIs. Claude's outputs should not be considered a substitute for professional medical advice or diagnosis.

Always carefully review and verify Claude's image interpretations, especially for high-stakes use cases. Do not use Claude for tasks requiring perfect precision or sensitive image analysis without human oversight.

---

## FAQ

<AccordionGroup>
  <Accordion title="What image file types does Claude support?">
    Claude currently supports JPEG, PNG, GIF, and WebP image formats, specifically:

    * `image/jpeg`
    * `image/png`
    * `image/gif`
    * `image/webp`

  </Accordion>

{" "}

  <Accordion title="Can Claude read image URLs?">
    Yes, Claude can now process images from URLs with our URL image source blocks in the API.
    Simply use the "url" source type instead of "base64" in your API requests.
    Example:

    ```json
    {
      "type": "image",
      "source": {
        "type": "url",
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
      }
    }
    ```

  </Accordion>

  <Accordion title="Is there a limit to the image file size I can upload?">
    Yes, there are limits:

    * API: Maximum 5MB per image
    * claude.ai: Maximum 10MB per image

    Images larger than these limits will be rejected and return an error when using our API.

  </Accordion>

  <Accordion title="How many images can I include in one request?">
    The image limits are:

    * Messages API: Up to 100 images per request
    * claude.ai: Up to 20 images per turn

    Requests exceeding these limits will be rejected and return an error.

  </Accordion>

{" "}

  <Accordion title="Does Claude read image metadata?">
    No, Claude does not parse or receive any metadata from images passed to it.
  </Accordion>

{" "}

  <Accordion title="Can I delete images I've uploaded?">
    No. Image uploads are ephemeral and not stored beyond the duration of the API
    request. Uploaded images are automatically deleted after they have been
    processed.
  </Accordion>

{" "}

  <Accordion title="Where can I find details on data privacy for image uploads?">
    Please refer to our privacy policy page for information on how we handle
    uploaded images and other data. We do not use uploaded images to train our
    models.
  </Accordion>

  <Accordion title="What if Claude's image interpretation seems wrong?">
    If Claude's image interpretation seems incorrect:

    1. Ensure the image is clear, high-quality, and correctly oriented.
    2. Try prompt engineering techniques to improve results.
    3. If the issue persists, flag the output in claude.ai (thumbs up/down) or contact our support team.

    Your feedback helps us improve!

  </Accordion>

  <Accordion title="Can Claude generate or edit images?">
    No, Claude is an image understanding model only. It can interpret and analyze images, but it cannot generate, produce, edit, manipulate, or create images.
  </Accordion>
</AccordionGroup>

---

## Dive deeper into vision

Ready to start building with images using Claude? Here are a few helpful resources:

- [Multimodal cookbook](https://github.com/anthropics/anthropic-cookbook/tree/main/multimodal): This cookbook has tips on [getting started with images](https://github.com/anthropics/anthropic-cookbook/blob/main/multimodal/getting%5Fstarted%5Fwith%5Fvision.ipynb) and [best practice techniques](https://github.com/anthropics/anthropic-cookbook/blob/main/multimodal/best%5Fpractices%5Ffor%5Fvision.ipynb) to ensure the highest quality performance with images. See how you can effectively prompt Claude with images to carry out tasks such as [interpreting and analyzing charts](https://github.com/anthropics/anthropic-cookbook/blob/main/multimodal/reading%5Fcharts%5Fgraphs%5Fpowerpoints.ipynb) or [extracting content from forms](https://github.com/anthropics/anthropic-cookbook/blob/main/multimodal/how%5Fto%5Ftranscribe%5Ftext.ipynb).
- [API reference](/en/api/messages): Visit our documentation for the Messages API, including example [API calls involving images](/en/api/messages-examples).

If you have any other questions, feel free to reach out to our [support team](https://support.anthropic.com/). You can also join our [developer community](https://www.anthropic.com/discord) to connect with other creators and get help from Anthropic experts.
