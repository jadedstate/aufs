package main

import (
	"fmt"
	"log"
	"os"

	"github.com/xitongsys/parquet-go/reader"
	"github.com/xitongsys/parquet-go/source/local" // Use the local file source for reading from disk
)

func main() {
	// Specify the path to your Parquet file
	parquetFilePath := "myfile.parquet"

	// Open the Parquet file
	fr, err := local.NewLocalFileReader(parquetFilePath)
	if err != nil {
		log.Fatalf("Failed to open Parquet file: %v", err)
	}
	defer fr.Close()

	// Create a new Parquet reader
	pr, err := reader.NewParquetReader(fr, nil, 1)
	if err != nil {
		log.Fatalf("Failed to create Parquet reader: %v", err)
	}
	defer pr.ReadStop()

	// Read the number of rows in the Parquet file
	numRows := int(pr.GetNumRows())
	if numRows == 0 {
		log.Println("No records found in the Parquet file.")
		return
	}

	// Read the first record from the Parquet file
	var result interface{}
	if err = pr.Read(&result); err != nil {
		log.Fatalf("Failed to read the Parquet file: %v", err)
	}

	// Display the first record
	fmt.Printf("First record: %v\n", result)
}
