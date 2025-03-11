<!-- Needle Banner -->
![Needle Banner](media/needle-banner-transparent.png)

<!-- Motto -->
*We have found the* ***Needle*** *in haystack!* 🪡🔍

<!-- Description -->
Needle is an open-source image retrieval database with high accuracy that can easily handle complex queries in natural language. It is **Fast**, **Efficient**, and **Precise**, outperforming state-of-the-art methods. Born from high-end research, Needle is designed to be accessible to everyone while delivering top-notch performance. Whether you’re a researcher, developer, or an enthusiast, Needle opens up innovative ways to explore your image datasets. ✨

<!-- Demonstration GIF -->
## See Needle in Action

<video controls>
  <source src="media/needle-demo.mp4" type="video/mp4">
</video>

*Watch as Needle transforms natural language queries into precise image retrieval results in real time.*


## Comparison to State-of-the-Art Methods
Curious how Needle measures up against other cutting-edge approaches? Here, you'll soon find performance plots that compare Needle with OPEN-AI CLIP image retrieval method for LVIS, Caltech256 and BDD100k.   

<!DOCTYPE html>
<div class="chart-container" style="font-family: system-ui, -apple-system, sans-serif;">
    <div style="background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.12);">
        <h3 style="margin-top: 0; color: #333;">User Preference Comparison</h3>
        <h4 style="margin-top: 0; color: #333;">Which one do you prefer for your queries?</h4>
        <div style="height: 400px;">
            <canvas id="preferenceChart"></canvas>
        </div>
    </div>
    <div style="background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.12);">
        <h3 style="margin-top: 0; color: #333;">Mean Average Precision Across Datasets</h3>
        <div style="height: 400px;">
            <canvas id="precisionChart"></canvas>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Preference Data
    const preferenceCtx = document.getElementById('preferenceChart').getContext('2d');
    new Chart(preferenceCtx, {
        type: 'bar',
        data: {
            labels: ['Needle', 'CLIP', 'Both', 'Neither'],
            datasets: [
                {
                    label: 'Needle',
                    data: [52.52, 23.23, 14.15, 10.1],
                    backgroundColor: '#bbddf5',
                    borderColor: '#367ea4',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw + '%';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Score (%)'
                    }
                }
            }
        }
    });

    // Precision Data
    const precisionCtx = document.getElementById('precisionChart').getContext('2d');
    new Chart(precisionCtx, {
        type: 'bar',
data: {
            labels: ['LVIS', 'Caltech256', 'BDD100K', 'COCO'],
            datasets: [
                {
                    label: 'Needle',
                    data: [0.323, 0.966, 0.711, 0.977],
                    backgroundColor: '#4caf50',
                    borderColor: '#2e7d32',
                    borderWidth: 1
                },
                {
                    label: 'CLIP',
                    data: [0.168, 0.939, 0.670, 0.952],
                    backgroundColor: '#2196f3',
                    borderColor: '#1565c0',
                    borderWidth: 1
                },
                {
                    label: 'ALIGN',
                    data: [0.207, 0.947, 0.573, 0.960],
                    backgroundColor: '#ff9800',
                    borderColor: '#ef6c00',
                    borderWidth: 1
                },
                {
                    label: 'FLAVA',
                    data: [0.180, 0.903, 0.698, 0.941],
                    backgroundColor: '#9c27b0',
                    borderColor: '#6a1b9a',
                    borderWidth: 1
                },
                {
                    label: 'BLIP + MiniLM',
                    data: [0.179, 0.838, 0.610, 0.951],
                    backgroundColor: '#e91e63',
                    borderColor: '#c2185b',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1,
                    title: {
                        display: true,
                        text: 'Mean Average Precision'
                    }
                }
            }
        }
    });
});
</script>

<!-- Call to Action -->
## Get Started Today!
Ready to revolutionize your image retrieval process? 🚀  
Install and test Needle now to experience the future of multimodal search!

> **Tip:** For detailed installation instructions, check out the [Getting Started](getting-started.md) section.

## Cite us 

For a deep dive into Needle’s theoretical guarantees and performance insights, please refer to our research paper.
- [**Needle: A Generative-AI Powered Monte Carlo Method for Answering Complex Natural Language Queries on Multi-modal Data**](https://arxiv.org/abs/2412.00639)

If you find Needle beneficial for your work, we kindly ask that you cite our work to help support continued innovation.

```bibtex  
@article{erfanian2024needle,
  title={Needle: A Generative-AI Powered Monte Carlo Method for Answering Complex Natural Language Queries on Multi-modal Data},
  author={Erfanian, Mahdi and Dehghankar, Mohsen and Asudeh, Abolfazl},
  journal={arXiv preprint arXiv:2412.00639},
  year={2024}
}
```  
