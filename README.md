# Big Data Assignment 2: Containerizing an AIS scanner project.

Author: Justina Pečiulytė, <justina.peciulyte@mif.stud.vu.lt>

### Overview

This project packages a simple command-line AIS data anomaly scanner as a Docker container. The implementation is based on the architecture originally developed for the first group assignment and relies on multiprocessing to analyze large datasets. With containerization, the user does not need to install Python or any dependencies on their machine -- the tool becomes more portable.

The application processes vessel movement data from AIS CSV files, performs validity checks, detects suspicious behavior, and returns a clean summary and an output file containing all flagged vessels. To demonstrate the functionality, two types of anomaly checks are included:

-   **"Going dark" anomaly**. Detects gaps longer than 4 hours between AIS where the vessel appears to have continued moving.
-   **Identity cloning/teleportation anomaly**. Detects unrealistic vessel movement by using geographic distance between consecutive pings to calculate speed.

The image is available on the Docker Hub image registry: <https://hub.docker.com/r/justinap4/ais_scanner>.

### Docker Image Creation

The Docker image was created using the following steps:

1.  Initialized the project by creating necessary files (Dockerfile, .dockerignore) using basic defaults provided by the CLI command 

```
  docker init
```

2.  Created a requirements.txt file using the `pipreqs` package.
4.  Specified additional files to be skipped during the bulding process in .dockerignore file.

5.  In the Dockerfile, set the needed parameters: 

    Selected a suitable lightweight base image:

    ```         
      FROM python:${3.13.7}-slim AS base
    ```

    Specified the working directory inside the container:

    ```         
       WORKDIR /app
    ```

    Defined the entry point to run the application:

    ```         
      ENTRYPOINT ["python", "main.py"]
    ```

6.  Built the Docker image using the CLI command:

```         
   docker build -t ais_scanner .
```

Input datasets are provided via bind mounts, so the image does not need to be rebuilt for different data files.

### Configurable Parameters

An input CSV file (MMSI, Timestamp, Latitude, Longitude, Type of mobile columns expected) must be specified for the container to run. A few optional parameters can be added to tune the tool's performance on an individual machine, change the printed summary, and choose an output file for saving the results of flagged vessels. Below is a list of all parameters and their descriptions:

| Parameter   | Description                                                         |
|-------------|---------------------------------------------------------------------|
| --input     | Path to AIS CSV input file (*must be mounted into the container*).    |
| --output    | Path to optional CSV output file.                                   |
| --top       | Number of top suspicious vessels to display (*default: 10*).          |
| --chunksize | Number of rows per chunk for processing (*default: 50000*).           |
| --workers   | Number of worker processes to use (*default: 4, sequential mode: 1*). |

### Expected Output

The tool prints a compact summary of the analyzed file, as well as saves vessel anomaly results to a CSV if output file is specified. 

### Run Instructions

1. Download the image:
```         
  docker pull justinap4/ais_scanner:latest
```

2. Check configurable parameters:
```       
  docker run --rm justinap4/ais_scanner --help
```

3. Run the project in the working directory and specified input file:
```         
  docker run --rm -v ${PWD}:/data justinap4/ais_scanner --input /data/sample_data.csv
```

Here, `-v $(pwd):/data` mounts local files into the container and `/data/sample_data.csv` is the input file inside the container.

### Challenges Encountered

Some minor issues were encountered while adapting the existing pipeline scripts for containerization. However, a more challenging part of the process was familiarizing with Docker concepts, such as command logic or Dockerfile requirements. In particular:

-   Choosing a base image and simplifying the Dockerfile. The chosen project was intended as a simple command line tool, thus, a lightweight slim Python base image and no specified port were sufficient.
-   Ensuring correct file paths inside the container and populating the .dockerignore file to avoid unnecessary files.
-   Understanding the difference between bind mounts and Docker volumes. Ultimately mounts were chosen, because the script relies on input files and does not need persistent data.
-   Handling errors when input files were not mounted properly.
-   Fixing Dockerfile warnings related to keyword casing. Although docker init command was used to streamline the creation process, some added lines to Dockerfile caused inconsistent casing, which returned a warning.

### Resources Used

The main source of information for the assignment's implementation was the official Docker documentation (<https://docs.docker.com/>) and the local Docker Desktop AI assistance tool. The tool was used to familiarize with the image pushing process using Docker Hub image registry.
