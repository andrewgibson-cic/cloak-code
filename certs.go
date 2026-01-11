package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"net"
	"os"
	"time"
)

// GenerateCA creates a new CA certificate and private key
func GenerateCA(certPath, keyPath string) error {
	// Check if CA already exists
	if _, err := os.Stat(certPath); err == nil {
		if _, err := os.Stat(keyPath); err == nil {
			fmt.Printf("✓ CA certificate already exists at %s\n", certPath)
			return nil
		}
	}

	fmt.Println("Generating new CA certificate...")

	// Generate private key
	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return fmt.Errorf("failed to generate private key: %w", err)
	}

	// Create certificate template
	template := x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject: pkix.Name{
			Organization:  []string{"env-sidecar"},
			Country:       []string{"US"},
			Province:      []string{"California"},
			Locality:      []string{"San Francisco"},
			CommonName:    "env-sidecar CA",
		},
		NotBefore:             time.Now(),
		NotAfter:              time.Now().AddDate(10, 0, 0), // 10 years
		KeyUsage:              x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature | x509.KeyUsageCertSign,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
		BasicConstraintsValid: true,
		IsCA:                  true,
		MaxPathLen:            0,
		DNSNames:              []string{"env-sidecar-ca"},
		IPAddresses:           []net.IP{net.ParseIP("127.0.0.1")},
	}

	// Self-sign the certificate
	certBytes, err := x509.CreateCertificate(rand.Reader, &template, &template, &privateKey.PublicKey, privateKey)
	if err != nil {
		return fmt.Errorf("failed to create certificate: %w", err)
	}

	// Write certificate to file
	certFile, err := os.Create(certPath)
	if err != nil {
		return fmt.Errorf("failed to create cert file: %w", err)
	}
	defer certFile.Close()

	if err := pem.Encode(certFile, &pem.Block{
		Type:  "CERTIFICATE",
		Bytes: certBytes,
	}); err != nil {
		return fmt.Errorf("failed to encode certificate: %w", err)
	}

	// Write private key to file
	keyFile, err := os.Create(keyPath)
	if err != nil {
		return fmt.Errorf("failed to create key file: %w", err)
	}
	defer keyFile.Close()

	if err := pem.Encode(keyFile, &pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(privateKey),
	}); err != nil {
		return fmt.Errorf("failed to encode private key: %w", err)
	}

	fmt.Printf("✓ CA certificate generated: %s\n", certPath)
	fmt.Printf("✓ CA private key generated: %s\n", keyPath)
	fmt.Println()
	fmt.Println("⚠️  IMPORTANT: Install the CA certificate in your devcontainer:")
	fmt.Printf("   Run: .devcontainer/setup-cert.sh\n")

	return nil
}

// LoadCACert loads the CA certificate from file
func LoadCACert(certPath, keyPath string) ([]byte, []byte, error) {
	certBytes, err := os.ReadFile(certPath)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to read CA certificate: %w", err)
	}

	keyBytes, err := os.ReadFile(keyPath)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to read CA private key: %w", err)
	}

	return certBytes, keyBytes, nil
}
